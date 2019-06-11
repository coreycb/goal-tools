#!/usr/bin/env python3

# Show the project settings for the repository that should be moved
# into the tree at a given branch.

import configparser
import copy
import glob
import io
import itertools
import logging
import os.path
import subprocess

from goal_tools.python3_first import projectconfig_ruamellib

from cliff import command
from ruamel.yaml import comments

LOG = logging.getLogger(__name__)


def find_project_settings_in_repo(repo_dir):
    yaml = projectconfig_ruamellib.YAML()
    candidate_bases = [
        '.zuul.yaml',
        'zuul.yaml',
        '.zuul.d/*.yaml',
        'zuul.d/*.yaml',
    ]
    for base in candidate_bases:
        pattern = os.path.join(repo_dir, base)
        for candidate in glob.glob(pattern):
            LOG.debug('looking for zuul config in %s',
                      candidate)
            with open(candidate, 'r', encoding='utf-8') as f:
                settings = yaml.load(f) or []
            for block in settings:
                if 'project' in block:
                    LOG.debug('using zuul config from %s',
                              candidate)
                    return (candidate, block, settings)
    LOG.debug('did not find in-tree project settings')
    return (None, {}, [])


def add_template_if_template(project, seeking_templ, adding_templ):
    changed = False
    templates = project.get('templates', [])
    supports_seeking = seeking_templ in templates
    tests_adding = adding_templ in templates
    if supports_seeking and not tests_adding:
        idx = templates.index(seeking_templ)
        templates.insert(idx + 1, adding_templ)
        changed = True
    return changed


def remove_template_if_template(project, removing_templ):
    changed = False
    templates = project.get('templates', [])
    supports_seeking = removing_templ in templates
    if supports_seeking:
        idx = templates.index(removing_templ)
        templates.remove(removing_templ)
        changed = True
    return changed

def py3_train_template_exists(project):
    py3_jobs_train = 'openstack-python3-train-jobs'
    py3_jobs_train_horizon = 'openstack-python3-train-jobs-horizon'
    py3_jobs_train_neutron = 'openstack-python3-train-jobs-neutron'
    py3_jobs_train_ceilometer = 'openstack-python3-train-jobs-ceilometer'
    py3_jobs_train_templates = [
        py3_jobs_train,
        py3_jobs_train_horizon,
        py3_jobs_train_neutron,
        py3_jobs_train_ceilometer
    ]
    templates = project.get('templates', [])
    for templ in py3_jobs_train_templates:
        if templ in templates:
            print("CCB found {} in {}".format(templ, templates))
            return True
    return False


def get_tox_envs(repo_dir):
    LOG.debug('getting tox environments in %s', repo_dir)
    try:
        result = subprocess.run(
            ['tox', '--listenvs'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=repo_dir,
        )
    except subprocess.CalledProcessError:
        LOG.info('unable to fetch tox environments for %s', repo_dir)
        return None
    text = result.stdout.decode('utf-8')
    return text.rstrip().split('\n')


def update_tox_envs(repo_dir, tox_envs):
    new_tox_envs = copy.deepcopy(tox_envs)
    py3_found = False
    py3_remove_envs = ['py34', 'py35']
    py3_add_envs = ['py36', 'py37']
    for env in new_tox_envs:
        if 'py3' in env:
            py3_found = True
    if py3_found:
        for env in itertools.chain(py3_remove_envs, py3_add_envs):
            if env in new_tox_envs:
                new_tox_envs.remove(env)
        index = 0
        if 'py27' in new_tox_envs:
            index = new_tox_envs.index('py27') + 1
        for env in reversed(py3_add_envs):
            new_tox_envs.insert(index, env)
    else:
        LOG.debug('no py3 tox environments found in %s', repo_dir)
    return new_tox_envs


def write_tox_envs(repo_dir, tox_envs, new_tox_envs):
    tox_file = os.path.join(repo_dir, 'tox.ini')
    if not os.path.exists(tox_file):
        LOG.info('no tox.ini file for %s', repo_dir)
        return
    with open(tox_file, 'r', encoding='utf-8') as f:
        tox_contents = f.read()
    LOG.debug('old tox environment is %s', tox_envs)
    LOG.debug('new tox environment is %s', new_tox_envs)
    tox_contents = tox_contents.replace(
        'envlist = {}'.format(','.join(tox_envs)),
        'envlist = {}'.format(','.join(new_tox_envs))
    )
    with open(tox_file, 'w', encoding='utf-8') as f:
        f.write(tox_contents)


def get_setup_classifier_tab(repo_dir):
    py3_classifier = 'Programming Language :: Python :: 3'
    LOG.debug('getting tab indentation string for classifier %s %s',
              repo_dir, py3_classifier)
    config = configparser.ConfigParser()
    config.read('setup.cfg')
    current_classifier = config['metadata']['classifier']
    if py3_classifier not in current_classifier:
        LOG.debug('no Python 3 classifier found in setup.cfg %s', repo_dir)
        return
    setup_file = os.path.join(repo_dir, 'setup.cfg')
    if not os.path.exists(setup_file):
        LOG.info('no setup.cfg file for %s', repo_dir)
        return
    with open(setup_file, 'r', encoding='utf-8') as f:
        for line in f:
            if py3_classifier in line:
                tab = line[:len(line)-len(line.lstrip())]
                LOG.debug('tab indentation found is |%s|', tab)
                return tab


def update_and_write_setup_classifiers(repo_dir, tab):
    py27_classifier = 'Programming Language :: Python :: 2.7'
    py3_classifier = 'Programming Language :: Python :: 3'
    py34_classifier = 'Programming Language :: Python :: 3.4'
    py35_classifier = 'Programming Language :: Python :: 3.5'
    py36_classifier = 'Programming Language :: Python :: 3.6'
    py37_classifier = 'Programming Language :: Python :: 3.7'
    py3_remove_classifiers = [py34_classifier, py35_classifier]
    py3_add_classifiers = [py36_classifier, py37_classifier]
    setup_file = os.path.join(repo_dir, 'setup.cfg')
    if not os.path.exists(setup_file):
        LOG.info('no setup.cfg file for %s', repo_dir)
        return
    with open(setup_file, 'r', encoding='utf-8') as f:
        setup_contents = f.read()
    LOG.debug('dropping all Python 3.x classifiers %s', repo_dir)
    for classifier in itertools.chain(
            py3_remove_classifiers, py3_add_classifiers):
        setup_contents = setup_contents.replace(
            '{}{}\n'.format(tab, classifier),
            ''
        )
    LOG.debug('adding Train Python 3.6 and 3.7 classifiers %s', repo_dir)
    setup_contents_orig = setup_contents
    setup_contents = setup_contents.replace(
        '{}{}\n'.format(tab, py3_classifier),
        '{}{}\n{}{}\n{}{}\n'.format(tab, py3_classifier,
                                    tab, py36_classifier,
                                    tab, py37_classifier)
    )
    if setup_contents == setup_contents_orig:
        setup_contents = setup_contents.replace(
            '{}{}\n'.format(tab, py27_classifier),
            '{}{}\n{}{}\n{}{}\n{}{}\n'.format(tab, py27_classifier,
                                              tab, py3_classifier,
                                              tab, py36_classifier,
                                              tab, py37_classifier)
    )
    with open(setup_file, 'w', encoding='utf-8') as f:
        return f.write(setup_contents)


class JobsAddPy3Train(command.Command):
    "update the in-tree project settings to include python 3 Train tests"

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            '--default-zuul-file',
            default='.zuul.yaml',
            help='the default file to create when one does not exist',
        )
        parser.add_argument(
            'repo_dir',
            help='the repository location',
        )
        return parser

    def take_action(self, parsed_args):
        LOG.debug('determining repository name from .gitreview')
        gitreview_filename = os.path.join(parsed_args.repo_dir, '.gitreview')
        cp = configparser.ConfigParser()
        cp.read(gitreview_filename)
        gerrit = cp['gerrit']
        repo = gerrit['project']
        if repo.endswith('.git'):
            repo = repo[:-4]
        LOG.info('working on %s', repo)

        in_repo = find_project_settings_in_repo(parsed_args.repo_dir)
        in_tree_file, in_tree_project, in_tree_settings = in_repo
        if not in_tree_file:
            raise RuntimeError('Could not find project settings in {}'.format(
                parsed_args.repo_dir))

        LOG.info('# {} add python3-train jobs'.format(repo))
        py37_jobs = 'openstack-python37-jobs'
        py36_jobs = 'openstack-python36-jobs'
        py35_jobs = 'openstack-python35-jobs'
        py37_jobs_horizon = 'openstack-python37-jobs-horizon'
        py36_jobs_horizon = 'openstack-python36-jobs-horizon'
        py35_jobs_horizon = 'openstack-python35-jobs-horizon'
        py37_jobs_neutron = 'openstack-python37-jobs-neutron'
        py36_jobs_neutron = 'openstack-python36-jobs-neutron'
        py35_jobs_neutron = 'openstack-python35-jobs-neutron'
        py37_jobs_ceilometer = 'openstack-python37-jobs-ceilometer'
        py36_jobs_ceilometer = 'openstack-python36-jobs-ceilometer'
        py35_jobs_ceilometer = 'openstack-python35-jobs-ceilometer'
        py37_jobs_nonvoting = 'openstack-python37-jobs-nonvoting'
        py36_jobs_nonvoting = 'openstack-python36-jobs-nonvoting'
        py35_jobs_nonvoting = 'openstack-python35-jobs-nonvoting'
        py3_jobs_train = 'openstack-python3-train-jobs'
        py3_jobs_train_horizon = 'openstack-python3-train-jobs-horizon'
        py3_jobs_train_neutron = 'openstack-python3-train-jobs-neutron'
        py3_jobs_train_ceilometer = 'openstack-python3-train-jobs-ceilometer'
        py37_tox = 'openstack-tox-py37'
        py36_tox = 'openstack-tox-py36'
        py35_tox = 'openstack-tox-py35'
        add_template_if_template_map = [
            [py37_jobs, py3_jobs_train],
            [py36_jobs, py3_jobs_train],
            [py35_jobs, py3_jobs_train],
            [py37_jobs_horizon, py3_jobs_train_horizon],
            [py36_jobs_horizon, py3_jobs_train_horizon],
            [py35_jobs_horizon, py3_jobs_train_horizon],
            [py37_jobs_neutron, py3_jobs_train_neutron],
            [py36_jobs_neutron, py3_jobs_train_neutron],
            [py35_jobs_neutron, py3_jobs_train_neutron],
            [py37_jobs_ceilometer, py3_jobs_train_ceilometer],
            [py36_jobs_ceilometer, py3_jobs_train_ceilometer],
            [py35_jobs_ceilometer, py3_jobs_train_ceilometer],
        ]
        remove_templates = [
            py37_jobs,
            py36_jobs,
            py35_jobs,
            py37_jobs_horizon,
            py36_jobs_horizon,
            py35_jobs_horizon,
            py37_jobs_neutron,
            py36_jobs_neutron,
            py35_jobs_neutron,
            py37_jobs_ceilometer,
            py36_jobs_ceilometer,
            py35_jobs_ceilometer,
            py37_jobs_nonvoting,
            py36_jobs_nonvoting,
            py35_jobs_nonvoting,
        ]
        changed = False
        for template_map in add_template_if_template_map:
            if add_template_if_template(
                    in_tree_project['project'],
                    template_map[0],
                    template_map[1]):
                changed = True
        for template in remove_templates:
            if remove_template_if_template(
                    in_tree_project['project'],
                    template):
                changed = True

        if (not changed and
                not py3_train_template_exists(in_tree_project['project'])):
            LOG.info('No updates needed for %s', repo)
            return 2

        LOG.info('# {} update python-train tox.ini'.format(repo))
        tox_envs = get_tox_envs(parsed_args.repo_dir)
        new_tox_envs = update_tox_envs(parsed_args.repo_dir, tox_envs)
        if new_tox_envs != tox_envs:
            changed = True
            write_tox_envs(parsed_args.repo_dir, tox_envs, new_tox_envs)

        LOG.info('# {} update python-train setup.cfg'.format(repo))
        tab = get_setup_classifier_tab(parsed_args.repo_dir)
        if update_and_write_setup_classifiers(parsed_args.repo_dir, tab):
            changed = True
