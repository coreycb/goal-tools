#!/bin/bash -e

bindir=$(dirname $0)

function usage {
    echo "do_infra.sh WORKDIR"
}

workdir="$1"

if [ -z "$workdir" ]; then
    usage
    exit 1
fi

REPOS="
openstack-infra/activity-board
openstack-infra/afsmon
openstack-infra/ansible-role-puppet
openstack-infra/askbot-theme
openstack-infra/bindep
openstack-infra/bugdaystats
openstack-infra/ciwatch
openstack-infra/devstack-gate
openstack/diskimage-builder
openstack-infra/elastic-recheck
openstack-infra/err2d2
openstack-infra/featuretracker
openstack-infra/gear
openstack-infra/gearman-plugin
openstack-infra/germqtt
openstack-infra/gerritbot
openstack-infra/gerritlib
openstack-infra/git-restack
openstack-infra/git-review
openstack-infra/gitdm
openstack-infra/glean
openstack-infra/grafyaml
openstack-infra/groups
openstack-infra/groups-static-pages
openstack-infra/infra-ansible
openstack-infra/infra-manual
openstack-infra/infra-specs
openstack-infra/irc-meetings
openstack-infra/jeepyb
openstack-infra/jenkins-job-builder
openstack-infra/js-afs-blob-store
openstack-infra/js-generator-openstack
openstack/js-openstack-lib
openstack-infra/js-openstack-registry-hooks
openstack-infra/lodgeit
openstack-infra/logstash-filters
openstack-infra/log-classify
openstack-infra/log_processor
openstack-infra/lpmqtt
openstack-infra/meetbot
openstack-infra/mqtt_statsd
openstack-infra/nose-html-output
openstack-infra/odsreg
openstack-dev/openstack-nose
openstack/openstack-planet
openstack-infra/openstack-zuul-jobs
openstack-infra/openstack-zuul-roles
openstack-infra/openstackid
openstack-infra/openstackid-resources
openstack-infra/openstackweb
openstack-infra/os-loganalyze
openstack-infra/project-config-example
openstack/ptgbot
openstack-infra/publications
openstack-infra/puppet-accessbot
openstack-infra/puppet-ansible
openstack-infra/puppet-apparmor
openstack-infra/puppet-askbot
openstack-infra/puppet-asterisk
openstack-infra/puppet-bandersnatch
openstack-infra/puppet-bugdaystats
openstack-infra/puppet-bup
openstack-infra/puppet-cgit
openstack-infra/puppet-ciwatch
openstack-infra/puppet-infra-cookiecutter
openstack-infra/puppet-dashboard
openstack-infra/puppet-diskimage_builder
openstack-infra/puppet-drupal
openstack-infra/puppet-elastic_recheck
openstack-infra/puppet-elasticsearch
openstack-infra/puppet-ethercalc
openstack-infra/puppet-etherpad_lite
openstack-infra/puppet-exim
openstack-infra/puppet-featuretracker
openstack-infra/puppet-germqtt
openstack-infra/puppet-gerrit
openstack-infra/puppet-gerritbot
openstack-infra/puppet-github
openstack-infra/puppet-grafyaml
openstack-infra/puppet-graphite
openstack-infra/puppet-haveged
openstack-infra/puppet-hound
openstack-infra/puppet-httpd
openstack-infra/puppet-infracloud
openstack-infra/puppet-ipsilon
openstack-infra/puppet-iptables
openstack-infra/puppet-jeepyb
openstack-infra/puppet-jenkins
openstack-infra/puppet-kerberos
openstack-infra/puppet-kibana
openstack-infra/puppet-lodgeit
openstack-infra/puppet-log_processor
openstack-infra/puppet-logrotate
openstack-infra/puppet-logstash
openstack-infra/puppet-lpmqtt
openstack-infra/puppet-mailman
openstack-infra/puppet-mediawiki
openstack-infra/puppet-meetbot
openstack-infra/puppet-mosquitto
openstack-infra/puppet-mqtt_statsd
openstack-infra/puppet-mysql_backup
openstack-infra/puppet-nodepool
openstack-infra/puppet-openafs
openstack-infra/puppet-openstack_health
openstack-infra/puppet-openstack_infra_spec_helper
openstack-infra/puppet-openstackci
openstack-infra/puppet-openstackid
openstack-infra/puppet-os_client_config
openstack-infra/puppet-packagekit
openstack-infra/puppet-pgsql_backup
openstack-infra/puppet-phabricator
openstack-infra/puppet-pip
openstack-infra/puppet-planet
openstack-infra/puppet-project_config
openstack-infra/puppet-ptgbot
openstack-infra/puppet-puppet
openstack-infra/puppet-redis
openstack-infra/puppet-refstack
openstack-infra/puppet-releasestatus
openstack-infra/puppet-reviewday
openstack-infra/puppet-simpleproxy
openstack-infra/puppet-snmpd
openstack-infra/puppet-ssh
openstack-infra/puppet-ssl_cert_check
openstack-infra/puppet-stackalytics
openstack-infra/puppet-statusbot
openstack-infra/puppet-storyboard
openstack-infra/puppet-subunit2sql
openstack-infra/puppet-sudoers
openstack-infra/puppet-tmpreaper
openstack-infra/puppet-translation_checksite
openstack-infra/puppet-ulimit
openstack-infra/puppet-unattended_upgrades
openstack-infra/puppet-unbound
openstack-infra/puppet-user
openstack-infra/puppet-vcsrepo
openstack-infra/puppet-vinz
openstack-infra/puppet-yum
openstack-infra/puppet-zanata
openstack-infra/puppet-zuul
openstack-infra/pynotedb
openstack-infra/pypi-mirror
openstack-infra/python-storyboardclient
openstack-infra/releasestatus
openstack-infra/reviewday
openstack-infra/reviewstats
openstack-infra/statusbot
openstack-infra/storyboard
openstack-infra/storyboard-webclient
openstack-infra/subunit2sql
openstack-infra/system-config
openstack-infra/trystack-site
openstack-infra/vinz
openstack-infra/yaml2ical
openstack-infra/zmq-event-publisher
openstack-infra/zuul-packaging
"

$bindir/do_team.sh "$workdir" "Infrastructure" $REPOS