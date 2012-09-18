#!/bin/bash
set -e

function log () {
    echo `date +['%T']` $@
}

function stamp () {
    $@ | perl -p -MPOSIX -e 'BEGIN {$!=1} $_ = strftime("[%T]", localtime) . "\t" . $_'
}

#---------------------------------------------------------------------------------------------------------
log "Initializing test suite on slave" @slavename@ "..."

######## Important parameters ########

CLUSTER_NAME=cluster_example
CONFIG_FILE=xrd_cluster_example.cf
CONFIG_PATH=/etc/xrootd/${CONFIG_FILE}

######################################

log "Fetching latest xrootd build ..."

mkdir -p tmp_initsh
rm -rf tmpinitsh/*
cd tmp_initsh
curl -sSkO "@proto@://master.xrd.test:@port@/showScript/utils/get_xrd_latest.py" > /dev/null
chmod 755 get_xrd_latest.py
rm -rf xrd_rpms
python get_xrd_latest.py
rm -rf xrd_rpms/slc-6-x86_64/xrootd-*-src-*.rpm
rm -rf xrd_rpms/slc-6-x86_64/xrootd-*-devel-*.rpm

#---------------------------------------------------------------------------------------------------------
log "Installing xrootd packages ..."

rpm -U \
xrd_rpms/slc-6-x86_64/xrootd-libs-*.rpm \
xrd_rpms/slc-6-x86_64/xrootd-client-*.rpm \
xrd_rpms/slc-6-x86_64/xrootd-client-admin-perl-*.rpm \
xrd_rpms/slc-6-x86_64/xrootd-fuse-*.rpm \
xrd_rpms/slc-6-x86_64/xrootd-server-*.rpm

cd ..

#---------------------------------------------------------------------------------------------------------
log "Downloading xrootd config file ${CONFIG_FILE} ..."

mkdir -p tmp_inittest
rm -rf tmp_inittest/*
cd tmp_inittest

if [ -f $CONFIG_PATH ]; then
    rm $CONFIG_PATH
fi
curl -sSkO "@proto@://master.xrd.test:@port@/downloadScript/clusters/${CLUSTER_NAME}/${CONFIG_FILE}" > /dev/null
mv $CONFIG_FILE $CONFIG_PATH

#---------------------------------------------------------------------------------------------------------
log "Creating service config file etc/sysconfig/xrootd ..."

SERVICE_CONFIG_FILE=/etc/sysconfig/xrootd
rm -rf $SERVICE_CONFIG_FILE
touch $SERVICE_CONFIG_FILE

# extracting machine name from hostname
arr=($(echo @slavename@ | tr "." " "))
NAME=${arr[0]}
UCASE_NAME=$(echo $NAME | tr a-z A-Z)

echo "
XROOTD_USER=daemon
XROOTD_GROUP=daemon

XROOTD_${UCASE_NAME}_OPTIONS=\" -l /var/log/xrootd/xrootd.log -c ${CONFIG_PATH} -k 7\"
CMSD_${UCASE_NAME}_OPTIONS=\" -l /var/log/xrootd/cmsd.log -c ${CONFIG_PATH} -k 7\"
PURD_${UCASE_NAME}_OPTIONS=\" -l /var/log/xrootd/purged.log -c ${CONFIG_PATH} -k 7\"
XFRD_${UCASE_NAME}_OPTIONS=\" -l /var/log/xrootd/xfrd.log -c ${CONFIG_PATH} -k 7\"

XROOTD_INSTANCES=\"${NAME}\"
CMSD_INSTANCES=\"${NAME}\"
PURD_INSTANCES=\"${NAME}\"
XFRD_INSTANCES=\"${NAME}\"
" > $SERVICE_CONFIG_FILE

#---------------------------------------------------------------------------------------------------------
log "Mounting storage disks for machine $NAME ..."

# Will be replaced by appropriate mount commands for each slave
@diskmounts@

#---------------------------------------------------------------------------------------------------------
log "Starting xrootd and cmsd for machine $NAME ..."
log "Config file: $CONFIG_PATH"

mkdir -p /var/log/xrootd

if [ -f /var/log/xrootd/${NAME}/xrootd.log ]; then
        rm /var/log/xrootd/${NAME}/xrootd.log
fi

if [ -f /var/log/xrootd/${NAME}/cmsd.log ]; then
        rm /var/log/xrootd/${NAME}/cmsd.log
fi

stamp service xrootd setup
stamp service xrootd start
stamp service cmsd start

#---------------------------------------------------------------------------------------------------------
N=5
log "Last ${N} lines of xrootd /var/log/xrootd/${NAME}/xrootd.log file:"
stamp tail --lines=$N /var/log/xrootd/${NAME}/xrootd.log

#---------------------------------------------------------------------------------------------------------
log "Last ${N} lines of cmsd /var/log/xrootd/${NAME}/cmsd.log file:"
stamp tail --lines=$N /var/log/xrootd/${NAME}/cmsd.log

log "Suite initialization complete."
