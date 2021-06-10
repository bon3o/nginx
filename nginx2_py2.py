#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Template App NGINX Cluster New API
"""
from __future__ import print_function
import json
import optparse
import requests
from protobix import DataContainer


class NginxAPI(object):
    """Class for NGINX Management API"""

    def __init__(self, hostname, user, password, port=8080, url='http://{0}:{1}/', zbx_host='127.0.0.1', zbx_port=10051,
                 sender=None):
        self.sender = sender
        self.zbx_host = zbx_host
        self.zbx_port = zbx_port
        self.url = url.format(hostname, port)
        self.s = requests.Session()
        self.s.auth = (user, password)

    def list_upstreams(self):
        """List all of the Nginx upstreams"""
        upstreams = []
        # noinspection PyBroadException
        try:
            data = self.s.get(self.url + 'api/3/http/upstreams').json()
            for upstream in data:
                # peers not configured
                if not data[upstream]['peers']:
                    continue
                zone = data[upstream]['zone']
                for peer in data[upstream]['peers']:
                    upstreams.append({
                        '{#UPSTREAM}': upstream,
                        '{#UPSTREAMPEER}': peer['id'],
                        '{#UPSTREAMSRV}': peer['server'],
                        '{#UPSTREAMNAME}': peer['name'],
                        '{#UPSTREAMZONE}': zone
                    })
        except:
            pass
        return upstreams

    def list_streams(self):
        """List all of the NGINX streams"""
        streams = []
        # noinspection PyBroadException
        try:
            data = self.s.get(self.url + 'api/3/stream/upstreams').json()
            for stream in data:
                # peers not configured
                if not data[stream]['peers']:
                    continue
                zone = data[stream]['zone']
                for peer in data[stream]['peers']:
                    streams.append({
                        '{#STREAM}': stream,
                        '{#STREAMPEER}': peer['id'],
                        '{#STREAMSRV}': peer['server'],
                        '{#STREAMNAME}': peer['name'],
                        '{#STREAMZONE}': zone
                    })
        except:
            pass
        return streams

    def short_list_upstreams(self):
        # noinspection PyBroadException
        try:
            data = self.s.get(self.url + 'api/3/http/upstreams').json()
            return [{'{#UPSTREAMSHORT}': upstream} for upstream in data if data and data[upstream]['peers']]
        except:
            pass
        return []

    def short_list_streams(self):
        # noinspection PyBroadException
        try:
            data = self.s.get(self.url + 'api/3/stream/upstreams').json()
            return [{'{#STREAMSHORT}': stream} for stream in data if data and data[stream]['peers']]
        except:
            pass
        return []

    def update_items(self):
        zbx_container = DataContainer('items', self.zbx_host, self.zbx_port)
        zbx_data = {}
        error_list = []
        try:
            data = self.s.get(self.url + 'api/3/http/upstreams').json()
            if data and not data.get('error'):
                for upstream in data:
                    # peers not configured
                    if not data[upstream]['peers']:
                        error_list.append('upstream {0} has no peers'.format(upstream))
                        continue
                    all_down = 1
                    for peer in data[upstream]['peers']:
                        if peer['state'] == 'up':
                            all_down = 0
                        zbx_data['state[{0},{1}]'.format(peer['server'], upstream)] = peer['state']
                        for key in ['1xx', '2xx', '3xx', '4xx', '5xx']:
                            zbx_data['responses_{0}[{1},{2}]'.format(key, peer['server'], upstream)] = \
                                peer['responses'][key]
                    zbx_data['overall_upstream_state[{0}]'.format(upstream)] = all_down
            # streams may absent
            data = self.s.get(self.url + 'api/3/stream/upstreams').json()
            if data and not data.get('error'):
                for stream in data:
                    # peers not configured
                    if not data[stream]['peers']:
                        error_list.append('stream {0} has no peers'.format(stream))
                        continue
                    all_down = 1
                    for peer in data[stream]['peers']:
                        if peer['state'] == 'up':
                            all_down = 0
                        zbx_data['state[{0},{1}]'.format(peer['server'], stream)] = peer['state']
                    zbx_data['overall_stream_state[{0}]'.format(stream)] = all_down
            if error_list:
                zbx_data['error_list'] = ', '.join(error_list)
            else:
                zbx_data['error_list'] = ''
            zbx_data = {self.sender: zbx_data}
            zbx_container.add(zbx_data)
            zbx_container.send(zbx_container)
        except Exception as e:
            print(e.message)


def main():
    """Command-line parameters and decoding for Zabbix use/consumption."""

    choices = ['update_items', 'list_upstreams', 'list_streams', 'short_list_upstreams', 'short_list_streams']
    parser = optparse.OptionParser()
    parser.add_option('--user', help='Nginx API username',
                      default='nginx-ui')
    parser.add_option('--password', help='Nginx API password',
                      default='J83yuvR')
    parser.add_option('--host', help='Nginx API host')
    parser.add_option('--port', help='Nginx API port', type='int', default=8080)
    parser.add_option('--check', type='choice', choices=choices, help='Type of check')
    parser.add_option('--sender', help='Sender parameter on calls to zabbix_sender')
    (options, args) = parser.parse_args()

    api = NginxAPI(hostname=options.host, user=options.user, password=options.password, sender=options.sender)

    if options.check == 'list_upstreams':
        print(json.dumps({'data': api.list_upstreams()}))
    elif options.check == 'list_streams':
        print(json.dumps({'data': api.list_streams()}))
    elif options.check == 'short_list_upstreams':
        print(json.dumps({'data': api.short_list_upstreams()}))
    elif options.check == 'short_list_streams':
        print(json.dumps({'data': api.short_list_streams()}))
    elif options.check == 'update_items':
        api.update_items()


if __name__ == '__main__':
    main()
