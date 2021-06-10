#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template App NGINX Cluster New API
"""

import json
import argparse
import requests
try:
    import protobix3 as protobix
except:
    import protobix

def data_send(data_to_send, pbx_server, pbx_port):
    zbx_datacontainer = protobix.DataContainer()
    zbx_datacontainer.server_active = pbx_server
    zbx_datacontainer.server_port = int(pbx_port)
    zbx_datacontainer.data_type = 'items'
    zbx_datacontainer.add(data_to_send)
    zbx_datacontainer.send()

class NginxAPI(object):
    """
    Class for NGINX Management API
    """

    def __init__(self, hostname, user, password, port=8080, url='http://{0}:{1}/', zbx_host='127.0.0.1', zbx_port=10051, sender=None):
        self.sender = sender
        self.zbx_host = zbx_host
        self.zbx_port = zbx_port
        self.url = url.format(hostname, port)
        self.s = requests.Session()
        self.s.auth = (user, password)

    def list_upstreams(self):
        keyList = []
        """
        List all of the Nginx upstreams
        """
        upstreams = []
        try:
            data = self.s.get(self.url + 'api/3/http/upstreams').json()
            for upstream in data:
                # peers not configured
                if not data[upstream]['peers']:
                    continue
                zone = data[upstream]['zone']
                
                for peer in data[upstream]['peers']:
                    key = "{0},{1}".format(upstream, peer['server'])
                    if key in keyList:
                        continue
                    keyList.append(key)
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
        """
        List all of the NGINX streams
        """
        streams = []
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
        try:
            data = self.s.get(self.url + 'api/3/http/upstreams').json()
            return [{'{#UPSTREAMSHORT}': upstream} for upstream in data if data and data[upstream]['peers']]
        except:
            pass
        return []

    def short_list_streams(self):
        try:
            data = self.s.get(self.url + 'api/3/stream/upstreams').json()
            return [{'{#STREAMSHORT}': stream} for stream in data if data and data[stream]['peers']]
        except:
            pass
        return []

    def update_items(self):
        reqCountTotal = 0
        reqCountCurrent = 0
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
                    peers_up = 0
                    for peer in data[upstream]['peers']:
                        if peer['state'] == 'up':
                            all_down = 0
                            peers_up += 1
                        zbx_data['state[{0},{1}]'.format(peer['server'], upstream)] = peer['state']
                        for key in ['1xx', '2xx', '3xx', '4xx', '5xx']:
                            zbx_data['responses_{0}[{1},{2}]'.format(key, peer['server'], upstream)] = \
                                peer['responses'][key]
                    zbx_data['overall_upstream_state[{0}]'.format(upstream)] = all_down
                    zbx_data['overall_upstream_up[{0}]'.format(upstream)] = peers_up
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

            reqs = self.s.get(self.url + "api/3/http/requests").json()
            if reqs and not reqs.get("error"):
                reqCountTotal = reqs.get("total")
                reqCountCurrent = reqs.get("current")

            zbx_data["requests_total"] = reqCountTotal
            zbx_data["requests_current"] = reqCountCurrent
            zbx_data = {self.sender: zbx_data}
            data_send(zbx_data, self.zbx_host, self.zbx_port)
        except Exception as e:
            print(e)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', help='Nginx API username', default='nginx-ui')
    parser.add_argument('--password', help='Nginx API password', default='J83yuvR')
    parser.add_argument('--host', help='Nginx API host', required=True)
    parser.add_argument('--port', help='Nginx API port', default=8080)
    parser.add_argument('--check', help='Type of check', required=True)
    parser.add_argument('--sender', help='Sender parameter on calls to zabbix_sender')
    return parser.parse_args()

def main():
    args = parse_args()

    api = NginxAPI(hostname=args.host, user=args.user, password=args.password, sender=args.sender)
    
    if args.check == 'list_upstreams':
        print(json.dumps({'data': api.list_upstreams()}))
    elif args.check == 'list_streams':
        print(json.dumps({'data': api.list_streams()}))
    elif args.check == 'short_list_upstreams':
        print(json.dumps({'data': api.short_list_upstreams()}))
    elif args.check == 'short_list_streams':
        print(json.dumps({'data': api.short_list_streams()}))
    elif args.check == 'update_items':
        api.update_items()

if __name__ == "__main__":
    main()