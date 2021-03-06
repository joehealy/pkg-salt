# -*- coding: utf-8 -*-
'''
Module for gathering and managing network information
'''

# Import python libs
import re
import logging

# Import salt libs
import salt.utils


log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only work on POSIX-like systems
    '''
    # Disable on Windows, a specific file module exists:
    if salt.utils.is_windows():
        return False

    return True


def ping(host):
    '''
    Performs a ping to a host

    CLI Example:

    .. code-block:: bash

        salt '*' network.ping archlinux.org
    '''
    cmd = 'ping -c 4 {0}'.format(salt.utils.network.sanitize_host(host))
    return __salt__['cmd.run'](cmd)


# FIXME: Does not work with: netstat 1.42 (2001-04-15) from net-tools
# 1.6.0 (Ubuntu 10.10)
def netstat():
    '''
    Return information on open ports and states

    CLI Example:

    .. code-block:: bash

        salt '*' network.netstat
    '''
    ret = []
    cmd = 'netstat -tulpnea'
    out = __salt__['cmd.run'](cmd).splitlines()
    for line in out:
        comps = line.split()
        if line.startswith('tcp'):
            ret.append({
                'inode': comps[7],
                'local-address': comps[3],
                'program': comps[8],
                'proto': comps[0],
                'recv-q': comps[1],
                'remote-address': comps[4],
                'send-q': comps[2],
                'state': comps[5],
                'user': comps[6]})
        if line.startswith('udp'):
            ret.append({
                'inode': comps[6],
                'local-address': comps[3],
                'program': comps[7],
                'proto': comps[0],
                'recv-q': comps[1],
                'remote-address': comps[4],
                'send-q': comps[2],
                'user': comps[5]})
    return ret


def traceroute(host):
    '''
    Performs a traceroute to a 3rd party host

    CLI Example:

    .. code-block:: bash

        salt '*' network.traceroute archlinux.org
    '''
    ret = []
    if not salt.utils.which('traceroute'):
        log.info('This minion does not have traceroute installed')
        return ret

    cmd = 'traceroute {0}'.format(salt.utils.network.sanitize_host(host))

    out = __salt__['cmd.run'](cmd)

    # Parse version of traceroute
    cmd2 = 'traceroute --version'
    out2 = __salt__['cmd.run'](cmd2)
    try:
        # Linux traceroute version looks like:
        #   Modern traceroute for Linux, version 2.0.19, Dec 10 2012
        # Darwin and FreeBSD traceroute version looks like: Version 1.4a12+[FreeBSD|Darwin]

        traceroute_version_raw = re.findall(r'.*[Vv]ersion (\d+)\.([\w\+]+)\.*(\w*)', out2)[0]
        log.debug('traceroute_version_raw: {0}'.format(traceroute_version_raw))
        traceroute_version = []
        for t in traceroute_version_raw:
            try:
                traceroute_version.append(int(t))
            except ValueError:
                traceroute_version.append(t)

        if len(traceroute_version) < 3:
            traceroute_version.append(0)

        log.debug('traceroute_version: {0}'.format(traceroute_version))

    except IndexError:
        traceroute_version = [0, 0, 0]

    for line in out.splitlines():
        if ' ' not in line:
            continue
        if line.startswith('traceroute'):
            continue

        if ('Darwin' in str(traceroute_version[1]) or 'FreeBSD' in str(traceroute_version[1])):
            try:
                traceline = re.findall(r'\s*(\d*)\s+(.*)\s+\((.*)\)\s+(.*)$', line)[0]
            except IndexError:
                traceline = re.findall(r'\s*(\d*)\s+(\*\s+\*\s+\*)', line)[0]

            log.debug('traceline: {0}'.format(traceline))
            delays = re.findall(r'(\d+\.\d+)\s*ms', str(traceline))

            try:
                if traceline[1] == '* * *':
                    result = {
                        'count': traceline[0],
                        'hostname': '*'
                    }
                else:
                    result = {
                        'count': traceline[0],
                        'hostname': traceline[1],
                        'ip': traceline[2],
                    }
                    for x in range(0, len(delays)):
                        result['ms{0}'.format(x+1)] = delays[x]
            except IndexError:
                result = {}

        elif (traceroute_version[0] >= 2 and traceroute_version[2] >= 14
                or traceroute_version[0] >= 2 and traceroute_version[1] > 0):
            comps = line.split('  ')
            if comps[1] == '* * *':
                result = {
                    'count': int(comps[0]),
                    'hostname': '*'}
            else:
                result = {
                    'count': int(comps[0]),
                    'hostname': comps[1].split()[0],
                    'ip': comps[1].split()[1].strip('()'),
                    'ms1': float(comps[2].split()[0]),
                    'ms2': float(comps[3].split()[0]),
                    'ms3': float(comps[4].split()[0])}
        else:
            comps = line.split()
            result = {
                'count': comps[0],
                'hostname': comps[1],
                'ip': comps[2],
                'ms1': comps[4],
                'ms2': comps[6],
                'ms3': comps[8],
                'ping1': comps[3],
                'ping2': comps[5],
                'ping3': comps[7]}

        ret.append(result)

    return ret


def dig(host):
    '''
    Performs a DNS lookup with dig

    CLI Example:

    .. code-block:: bash

        salt '*' network.dig archlinux.org
    '''
    cmd = 'dig {0}'.format(salt.utils.network.sanitize_host(host))
    return __salt__['cmd.run'](cmd)


def arp():
    '''
    Return the arp table from the minion

    CLI Example:

    .. code-block:: bash

        salt '*' '*' network.arp
    '''
    ret = {}
    out = __salt__['cmd.run']('arp -an')
    for line in out.splitlines():
        comps = line.split()
        if len(comps) < 4:
            continue
        ret[comps[3]] = comps[1].strip('(').strip(')')
    return ret


def interfaces():
    '''
    Return a dictionary of information about all the interfaces on the minion

    CLI Example:

    .. code-block:: bash

        salt '*' network.interfaces
    '''
    return salt.utils.network.interfaces()


def hw_addr(iface):
    '''
    Return the hardware address (a.k.a. MAC address) for a given interface

    CLI Example:

    .. code-block:: bash

        salt '*' network.hw_addr eth0
    '''
    return salt.utils.network.hw_addr(iface)

# Alias hwaddr to preserve backward compat
hwaddr = hw_addr


def subnets():
    '''
    Returns a list of subnets to which the host belongs

    CLI Example:

    .. code-block:: bash

        salt '*' network.subnets
    '''
    return salt.utils.network.subnets()


def in_subnet(cidr):
    '''
    Returns True if host is within specified subnet, otherwise False.

    CLI Example:

    .. code-block:: bash

        salt '*' network.in_subnet 10.0.0.0/16
    '''
    return salt.utils.network.in_subnet(cidr)


def ip_addrs(interface=None, include_loopback=False):
    '''
    Returns a list of IPv4 addresses assigned to the host. 127.0.0.1 is
    ignored, unless 'include_loopback=True' is indicated. If 'interface' is
    provided, then only IP addresses from that interface will be returned.

    CLI Example:

    .. code-block:: bash

        salt '*' network.ip_addrs
    '''
    return salt.utils.network.ip_addrs(interface=interface,
                                       include_loopback=include_loopback)

ipaddrs = ip_addrs


def ip_addrs6(interface=None, include_loopback=False):
    '''
    Returns a list of IPv6 addresses assigned to the host. ::1 is ignored,
    unless 'include_loopback=True' is indicated. If 'interface' is provided,
    then only IP addresses from that interface will be returned.

    CLI Example:

    .. code-block:: bash

        salt '*' network.ip_addrs6
    '''
    return salt.utils.network.ip_addrs6(interface=interface,
                                        include_loopback=include_loopback)

ipaddrs6 = ip_addrs6
