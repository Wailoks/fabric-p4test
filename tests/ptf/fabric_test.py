# Copyright 2013-present Barefoot Networks, Inc.
# Copyright 2018-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import struct
import time
from operator import ior

from p4.v1 import p4runtime_pb2
from ptf import testutils as testutils
from ptf.mask import Mask
from scapy.contrib.mpls import MPLS
from scapy.layers.inet import IP, UDP, TCP
from scapy.layers.l2 import Ether, Dot1Q
from scapy.layers.ppp import PPPoE, PPP
from scapy.fields import BitField, ByteField, ShortField, IntField
from scapy.packet import bind_layers


import xnt
from base_test import P4RuntimeTest, stringify, mac_to_binary, ipv4_to_binary

DEFAULT_PRIORITY = 10

FORWARDING_TYPE_BRIDGING = 0
FORWARDING_TYPE_UNICAST_IPV4 = 2
FORWARDING_TYPE_MPLS = 1

CPU_CLONE_SESSION_ID = 511

DEFAULT_MPLS_TTL = 64
MIN_PKT_LEN = 80

UDP_GTP_PORT = 2152
DEFAULT_GTP_TUNNEL_SPORT = 1234  # arbitrary, but different from 2152

ETH_TYPE_ARP = 0x0806
ETH_TYPE_IPV4 = 0x0800
ETH_TYPE_VLAN = 0x8100
ETH_TYPE_QINQ = 0x88a8
ETH_TYPE_PPPOE = 0x8864
ETH_TYPE_MPLS_UNICAST = 0x8847

IP_PROTO_UDP = 0x11
IP_PROTO_TCP = 0x06
IP_PROTO_ICMP = 0x01

# In case the "correct" version of scapy (from p4lang) is not installed, we
# provide the INT header formats in xnt.py
# import scapy.main
# scapy.main.load_contrib("xnt")
# INT_META_HDR = scapy.contrib.xnt.INT_META_HDR
# INT_L45_HEAD = scapy.contrib.xnt.INT_L45_HEAD
# INT_L45_TAIL = scapy.contrib.xnt.INT_L45_TAIL
INT_META_HDR = xnt.INT_META_HDR
INT_L45_HEAD = xnt.INT_L45_HEAD
INT_L45_TAIL = xnt.INT_L45_TAIL

BROADCAST_MAC = ":".join(["ff"] * 6)
MAC_MASK = ":".join(["ff"] * 6)
SWITCH_MAC = "00:00:00:00:aa:01"
SWITCH_IPV4 = "192.168.0.1"
SPINE_MAC = "00:00:00:00:aa:02"

ZERO_MAC = "00:00:00:00:00:00"
HOST1_MAC = "00:00:00:00:00:01"
HOST2_MAC = "00:00:00:00:00:02"
HOST3_MAC = "00:00:00:00:00:03"

HOST1_IPV4 = "10.0.1.1"
HOST2_IPV4 = "10.0.2.1"
HOST3_IPV4 = "10.0.3.1"
HOST4_IPV4 = "10.0.4.1"
S1U_ENB_IPV4 = "119.0.0.10"
S1U_ENB_MAC = "00:00:00:00:00:eb"
S1U_SGW_IPV4 = "140.0.0.2"
UE_IPV4 = "16.255.255.252"

DBUF_MAC = "00:00:00:0d:b0:0f"
DBUF_IPV4 = "141.0.0.1"
DBUF_DRAIN_DST_IPV4 = "142.0.0.1"
DBUF_FAR_ID = 1023
DBUF_TEID = 0

SPGW_DIRECTION_UPLINK = 1
SPGW_DIRECTION_DOWNLINK = 2
SPGW_IFACE_ACCESS = 1
SPGW_IFACE_CORE = 2
SPGW_IFACE_FROM_DBUF = 3

VLAN_ID_1 = 100
VLAN_ID_2 = 200
VLAN_ID_3 = 300
DEFAULT_VLAN = 4094

MPLS_LABEL_1 = 100
MPLS_LABEL_2 = 200

UPLINK_TEID = 0xeeffc0f0
DOWNLINK_TEID = 0xeeffc0f1
UPLINK_PDR_CTR_ID = 1
DOWNLINK_PDR_CTR_ID = 2
UPLINK_FAR_ID = 23
DOWNLINK_FAR_ID = 24

# INT instructions
INT_SWITCH_ID = 1 << 15
INT_IG_EG_PORT = 1 << 14
INT_HOP_LATENCY = 1 << 13
INT_QUEUE_OCCUPANCY = 1 << 12
INT_IG_TSTAMP = 1 << 11
INT_EG_TSTAMP = 1 << 10
INT_QUEUE_CONGESTION = 1 << 9
INT_EG_PORT_TX = 1 << 8
INT_ALL_INSTRUCTIONS = [INT_SWITCH_ID, INT_IG_EG_PORT, INT_HOP_LATENCY,
                        INT_QUEUE_OCCUPANCY, INT_IG_TSTAMP, INT_EG_TSTAMP,
                        INT_QUEUE_CONGESTION, INT_EG_PORT_TX]

INT_INS_TO_NAME = {
    INT_SWITCH_ID: "switch_id",
    INT_IG_EG_PORT: "ig_eg_port",
    INT_HOP_LATENCY: "hop_latency",
    INT_QUEUE_OCCUPANCY: "queue_occupancy",
    INT_IG_TSTAMP: "ig_tstamp",
    INT_EG_TSTAMP: "eg_tstamp",
    INT_QUEUE_CONGESTION: "queue_congestion",
    INT_EG_PORT_TX: "eg_port_tx"

}

PPPOE_CODE_SESSION_STAGE = 0x00

PPPOED_CODE_PADI = 0x09
PPPOED_CODE_PADO = 0x07
PPPOED_CODE_PADR = 0x19
PPPOED_CODE_PADS = 0x65
PPPOED_CODE_PADT = 0xa7

PPPOED_CODES = (
    PPPOED_CODE_PADI,
    PPPOED_CODE_PADO,
    PPPOED_CODE_PADR,
    PPPOED_CODE_PADS,
    PPPOED_CODE_PADT,
)

PORT_TYPE_OTHER     = b"\x00"
PORT_TYPE_EDGE      = b"\x01"
PORT_TYPE_INFRA     = b"\x02"
PORT_TYPE_INTERNAL  = b"\x03"

class GTP(Packet):
    name = "GTP Header"
    fields_desc = [
        BitField("version", 1, 3),
        BitField("PT", 1, 1),
        BitField("reserved", 0, 1),
        BitField("E", 0, 1),
        BitField("S", 0, 1),
        BitField("PN", 0, 1),
        ByteField("gtp_type", 255),
        ShortField("length", None),
        IntField("teid", 0)
    ]

    def post_build(self, pkt, payload):
        pkt += payload
        # Set the length field if it is unset
        if self.length is None:
            length = len(pkt) - 8
            pkt = pkt[:2] + struct.pack("!H", length) + pkt[4:]
        return pkt


# Register our GTP header with scapy for dissection
bind_layers(UDP, GTP, dport=UDP_GTP_PORT)
bind_layers(GTP, IP)


def pkt_mac_swap(pkt):
    orig_dst = pkt[Ether].dst
    pkt[Ether].dst = pkt[Ether].src
    pkt[Ether].src = orig_dst
    return pkt


def pkt_route(pkt, mac_dst):
    new_pkt = pkt.copy()
    new_pkt[Ether].src = pkt[Ether].dst
    new_pkt[Ether].dst = mac_dst
    return new_pkt


def pkt_add_vlan(pkt, vlan_vid=10, vlan_pcp=0, dl_vlan_cfi=0):
    return Ether(src=pkt[Ether].src, dst=pkt[Ether].dst) / \
           Dot1Q(prio=vlan_pcp, id=dl_vlan_cfi, vlan=vlan_vid) / \
           pkt[Ether].payload


def pkt_add_inner_vlan(pkt, vlan_vid=10, vlan_pcp=0, dl_vlan_cfi=0):
    assert Dot1Q in pkt
    return Ether(src=pkt[Ether].src, dst=pkt[Ether].dst, type=ETH_TYPE_VLAN) / \
           Dot1Q(prio=pkt[Dot1Q].prio, id=pkt[Dot1Q].id, vlan=pkt[Dot1Q].vlan) / \
           Dot1Q(prio=vlan_pcp, id=dl_vlan_cfi, vlan=vlan_vid) / \
           pkt[Dot1Q].payload


def pkt_add_pppoe(pkt, type, code, session_id):
    return Ether(src=pkt[Ether].src, dst=pkt[Ether].dst) / \
           PPPoE(version=1, type=type, code=code, sessionid=session_id) / \
           PPP() / pkt[Ether].payload


def pkt_add_mpls(pkt, label, ttl, cos=0, s=1):
    return Ether(src=pkt[Ether].src, dst=pkt[Ether].dst) / \
           MPLS(label=label, cos=cos, s=s, ttl=ttl) / \
           pkt[Ether].payload


def pkt_add_gtp(pkt, out_ipv4_src, out_ipv4_dst, teid,
                sport=DEFAULT_GTP_TUNNEL_SPORT, dport=UDP_GTP_PORT):
    payload = pkt[Ether].payload
    return Ether(src=pkt[Ether].src, dst=pkt[Ether].dst) / \
           IP(src=out_ipv4_src, dst=out_ipv4_dst, tos=0,
              id=0x1513, flags=0, frag=0) / \
           UDP(sport=sport, dport=dport, chksum=0) / \
           GTP(teid=teid) / \
           payload


def pkt_remove_vlan(pkt):
    assert Dot1Q in pkt
    payload = pkt[Dot1Q:1].payload
    return Ether(src=pkt[Ether].src, dst=pkt[Ether].dst, type=pkt[Dot1Q:1].type) / \
           payload


def pkt_decrement_ttl(pkt):
    if IP in pkt:
        pkt[IP].ttl -= 1
    return pkt


class FabricTest(P4RuntimeTest):

    def __init__(self):
        super(FabricTest, self).__init__()
        self.next_mbr_id = 1

    def get_next_mbr_id(self):
        mbr_id = self.next_mbr_id
        self.next_mbr_id = self.next_mbr_id + 1
        return mbr_id

    def setUp(self):
        super(FabricTest, self).setUp()
        self.port1 = self.swports(0)
        self.port2 = self.swports(1)
        self.port3 = self.swports(2)

    def setup_int(self):
        self.send_request_add_entry_to_action(
            "int_egress.int_prep", None, "int_egress.int_transit",
            [("switch_id", stringify(1, 4))])

        req = self.get_new_write_request()
        for i in xrange(16):
            base = "int_set_header_0003_i"
            mf = self.Exact("hdr.int_header.instruction_mask_0003",
                            stringify(i, 1))
            action = "int_metadata_insert." + base + str(i)
            self.push_update_add_entry_to_action(
                req,
                "int_metadata_insert.int_inst_0003", [mf],
                action, [])
        self.write_request(req)

        req = self.get_new_write_request()
        for i in xrange(16):
            base = "int_set_header_0407_i"
            mf = self.Exact("hdr.int_header.instruction_mask_0407",
                            stringify(i, 1))
            action = "int_metadata_insert." + base + str(i)
            self.push_update_add_entry_to_action(
                req,
                "int_metadata_insert.int_inst_0407", [mf],
                action, [])
        self.write_request(req)

    def setup_port(self, port_id, vlan_id, port_type, tagged=False, double_tagged=False, inner_vlan_id=0):
        if double_tagged:
            self.set_ingress_port_vlan(ingress_port=port_id, vlan_id=vlan_id,
                                       vlan_valid=True, inner_vlan_id=inner_vlan_id, port_type=port_type)
        elif tagged:
            self.set_ingress_port_vlan(ingress_port=port_id, vlan_id=vlan_id,
                                       vlan_valid=True, port_type=port_type)
            self.set_egress_vlan(egress_port=port_id, vlan_id=vlan_id, push_vlan=True)
        else:
            self.set_ingress_port_vlan(ingress_port=port_id,
                                       vlan_valid=False, internal_vlan_id=vlan_id, port_type=port_type)
            self.set_egress_vlan(egress_port=port_id, vlan_id=vlan_id, push_vlan=False)

    def set_ingress_port_vlan(self, ingress_port,
                              vlan_valid=False,
                              vlan_id=0,
                              internal_vlan_id=0,
                              inner_vlan_id=None,
                              port_type=PORT_TYPE_EDGE,
                              ):
        ingress_port_ = stringify(ingress_port, 2)
        vlan_valid_ = '\x01' if vlan_valid else '\x00'
        vlan_id_ = stringify(vlan_id, 2)
        vlan_id_mask_ = stringify(4095 if vlan_valid else 0, 2)
        new_vlan_id_ = stringify(internal_vlan_id, 2)
        action_name = "permit" if vlan_valid else "permit_with_internal_vlan"
        action_params = [("port_type", port_type)]
        if not vlan_valid:
            action_params.append(("vlan_id", new_vlan_id_))
        matches = [self.Exact("ig_port", ingress_port_),
                   self.Exact("vlan_is_valid", vlan_valid_),
                   self.Ternary("vlan_id", vlan_id_, vlan_id_mask_)]
        if inner_vlan_id is not None:
            # Match on inner_vlan, only when explicitly requested
            inner_vlan_id_ = stringify(inner_vlan_id, 2)
            inner_vlan_id_mask_ = stringify(4095, 2)
            matches.append(self.Ternary("inner_vlan_id", inner_vlan_id_, inner_vlan_id_mask_))

        self.send_request_add_entry_to_action(
            "filtering.ingress_port_vlan",
            matches,
            "filtering." + action_name, action_params,
            DEFAULT_PRIORITY)

    def set_egress_vlan(self, egress_port, vlan_id, push_vlan=False):
        egress_port = stringify(egress_port, 2)
        vlan_id = stringify(vlan_id, 2)
        action_name = "push_vlan" if push_vlan else "pop_vlan"
        self.send_request_add_entry_to_action(
            "egress_next.egress_vlan",
            [self.Exact("vlan_id", vlan_id),
             self.Exact("eg_port", egress_port)],
            "egress_next." + action_name, [])

    def set_forwarding_type(self, ingress_port, eth_dstAddr, ethertype=ETH_TYPE_IPV4,
                            fwd_type=FORWARDING_TYPE_UNICAST_IPV4):
        ingress_port_ = stringify(ingress_port, 2)
        if ethertype == ETH_TYPE_IPV4:
            ethertype_ = stringify(0, 2)
            ethertype_mask_ = stringify(0, 2)
            ip_eth_type = stringify(ethertype, 2)
        elif ethertype == ETH_TYPE_MPLS_UNICAST:
            ethertype_ = stringify(ETH_TYPE_MPLS_UNICAST, 2)
            ethertype_mask_ = stringify(0xFFFF, 2)
            # FIXME: this will work only for MPLS+IPv4 traffic
            ip_eth_type = stringify(ETH_TYPE_IPV4, 2)
        else:
            # TODO: what should we match on? I should never reach this point.
            return
        fwd_type_ = stringify(fwd_type, 1)
        matches = [self.Exact("ig_port", ingress_port_),
                   self.Ternary("eth_type", ethertype_, ethertype_mask_),
                   self.Exact("ip_eth_type", ip_eth_type)]
        if eth_dstAddr is not None:
            eth_dstAddr_ = mac_to_binary(eth_dstAddr)
            eth_mask_ = mac_to_binary(MAC_MASK)
            matches.append(self.Ternary("eth_dst", eth_dstAddr_, eth_mask_))
        self.send_request_add_entry_to_action(
            "filtering.fwd_classifier",
            matches,
            "filtering.set_forwarding_type",
            [("fwd_type", fwd_type_)],
            priority=DEFAULT_PRIORITY)

    def add_bridging_entry(self, vlan_id, eth_dstAddr, eth_dstAddr_mask, next_id):
        vlan_id_ = stringify(vlan_id, 2)
        mk = [self.Exact("vlan_id", vlan_id_)]
        if eth_dstAddr is not None:
            eth_dstAddr_ = mac_to_binary(eth_dstAddr)
            eth_dstAddr_mask_ = mac_to_binary(eth_dstAddr_mask)
            mk.append(self.Ternary(
                "eth_dst", eth_dstAddr_, eth_dstAddr_mask_))
        next_id_ = stringify(next_id, 4)
        self.send_request_add_entry_to_action(
            "forwarding.bridging", mk,
            "forwarding.set_next_id_bridging", [("next_id", next_id_)],
            DEFAULT_PRIORITY)

    def add_forwarding_routing_v4_entry(self, ipv4_dstAddr, ipv4_pLen,
                                        next_id):
        next_id_ = stringify(next_id, 4)
        if ipv4_pLen > 0:
            ipv4_dstAddr_ = ipv4_to_binary(ipv4_dstAddr)
            mk = [self.Lpm("ipv4_dst", ipv4_dstAddr_, ipv4_pLen)]
        else:
            mk = None
        self.send_request_add_entry_to_action(
            "forwarding.routing_v4", mk,
            "forwarding.set_next_id_routing_v4", [("next_id", next_id_)])

    def add_forwarding_mpls_entry(self, label, next_id):
        label_ = stringify(label, 3)
        next_id_ = stringify(next_id, 4)
        self.send_request_add_entry_to_action(
            "forwarding.mpls",
            [self.Exact("mpls_label", label_)],
            "forwarding.pop_mpls_and_next", [("next_id", next_id_)])

    def add_forwarding_acl_punt_to_cpu(self, eth_type=None):
        eth_type_ = stringify(eth_type, 2)
        eth_type_mask = stringify(0xFFFF, 2)
        self.send_request_add_entry_to_action(
            "acl.acl",
            [self.Ternary("eth_type", eth_type_, eth_type_mask)],
            "acl.punt_to_cpu", [],
            DEFAULT_PRIORITY)

    def add_forwarding_acl_set_clone_session_id(self, eth_type=None, clone_group_id=None):
        eth_type_ = stringify(eth_type, 2)
        eth_type_mask = stringify(0xFFFF, 2)
        clone_group_id_ = stringify(clone_group_id, 4)
        self.send_request_add_entry_to_action(
            "acl.acl",
            [self.Ternary("eth_type", eth_type_, eth_type_mask)],
            "acl.set_clone_session_id", [("clone_id", clone_group_id_)],
            DEFAULT_PRIORITY)

    def add_forwarding_acl_drop(
        self, ipv4_src=None, ipv4_dst=None, ip_proto=None,
        l4_sport=None, l4_dport=None,
    ):
        # Send only if the match keys are not empty
        matches = []
        if ipv4_src:
            ipv4_src_ = ipv4_to_binary(ipv4_src)
            ipv4_src_mask = stringify(0xFFFFFFFF, 4)
            matches.append(self.Ternary("ipv4_src", ipv4_src_, ipv4_src_mask))
        if ipv4_dst:
            ipv4_dst_ = ipv4_to_binary(ipv4_dst)
            ipv4_dst_mask = stringify(0xFFFFFFFF, 4)
            matches.append(self.Ternary("ipv4_dst", ipv4_dst_, ipv4_dst_mask))
        if ip_proto:
            ip_proto_ = stringify(ip_proto, 1)
            ip_proto_mask = stringify(0xFF, 1)
            matches.append(self.Ternary("ip_proto", ip_proto_, ip_proto_mask))
        if l4_sport:
            l4_sport_ = stringify(l4_sport, 2)
            l4_sport_mask = stringify(0xFFFF, 2)
            matches.append(self.Ternary("l4_sport", l4_sport_, l4_sport_mask))
        if l4_dport:
            l4_dport_ = stringify(l4_dport, 2)
            l4_dport_mask = stringify(0xFFFF, 2)
            matches.append(self.Ternary("l4_dport", l4_dport_, l4_dport_mask))
        if matches:
            self.send_request_add_entry_to_action(
                "acl.acl",
                matches,
                "acl.drop",
                [],
                DEFAULT_PRIORITY)

    def add_forwarding_acl_next(
        self, next_id, port_type, ipv4_src=None, ipv4_dst=None, ip_proto=None,
        l4_sport=None, l4_dport=None
    ):
        # Send only if the match keys are not empty
        next_id_ = stringify(next_id, 4)
        port_type_mask = b"\x03"
        matches = [self.Ternary("port_type",port_type, port_type_mask)]
        if ipv4_src:
            ipv4_src_ = ipv4_to_binary(ipv4_src)
            ipv4_src_mask = stringify(0xFFFFFFFF, 4)
            matches.append(self.Ternary("ipv4_src", ipv4_src_, ipv4_src_mask))
        if ipv4_dst:
            ipv4_dst_ = ipv4_to_binary(ipv4_dst)
            ipv4_dst_mask = stringify(0xFFFFFFFF, 4)
            matches.append(self.Ternary("ipv4_dst", ipv4_dst_, ipv4_dst_mask))
        if ip_proto:
            ip_proto_ = stringify(ip_proto, 1)
            ip_proto_mask = stringify(0xFF, 1)
            matches.append(self.Ternary("ip_proto", ip_proto_, ip_proto_mask))
        if l4_sport:
            l4_sport_ = stringify(l4_sport, 2)
            l4_sport_mask = stringify(0xFFFF, 2)
            matches.append(self.Ternary("l4_sport", l4_sport_, l4_sport_mask))
        if l4_dport:
            l4_dport_ = stringify(l4_dport, 2)
            l4_dport_mask = stringify(0xFFFF, 2)
            matches.append(self.Ternary("l4_dport", l4_dport_, l4_dport_mask))
        if matches:
            self.send_request_add_entry_to_action(
                "acl.acl",
                matches,
                "acl.set_next_id_acl",
                [("next_id", next_id_)],
                DEFAULT_PRIORITY)

    def add_xconnect(self, next_id, port1, port2):
        next_id_ = stringify(next_id, 4)
        port1_ = stringify(port1, 2)
        port2_ = stringify(port2, 2)
        for (inport, outport) in ((port1_, port2_), (port2_, port1_)):
            self.send_request_add_entry_to_action(
                "next.xconnect",
                [self.Exact("next_id", next_id_),
                 self.Exact("ig_port", inport)],
                "next.output_xconnect", [("port_num", outport)])

    def add_next_output(self, next_id, egress_port):
        egress_port_ = stringify(egress_port, 2)
        self.add_next_hashed_indirect_action(
            next_id,
            "next.output_hashed", [("port_num", egress_port_)])

    def add_next_output_simple(self, next_id, egress_port):
        next_id_ = stringify(next_id, 4)
        egress_port_ = stringify(egress_port, 2)
        self.send_request_add_entry_to_action(
            "next.simple",
            [self.Exact("next_id", next_id_)],
            "next.output_simple", [("port_num", egress_port_)])

    def add_next_multicast(self, next_id, mcast_group_id):
        next_id_ = stringify(next_id, 4)
        mcast_group_id_ = stringify(mcast_group_id, 2)
        self.send_request_add_entry_to_action(
            "next.multicast",
            [self.Exact("next_id", next_id_)],
            "next.set_mcast_group_id", [("group_id", mcast_group_id_)])

    def add_next_multicast_simple(self, next_id, mcast_group_id):
        next_id_ = stringify(next_id, 4)
        mcast_group_id_ = stringify(mcast_group_id, 2)
        self.send_request_add_entry_to_action(
            "next.multicast",
            [self.Exact("next_id", next_id_)],
            "next.set_mcast_group", [("gid", mcast_group_id_)])

    def add_next_routing(self, next_id, egress_port, smac, dmac):
        egress_port_ = stringify(egress_port, 2)
        smac_ = mac_to_binary(smac)
        dmac_ = mac_to_binary(dmac)
        self.add_next_hashed_group_action(
            next_id,
            egress_port,
            [
                ["next.routing_hashed", [("port_num", egress_port_), ("smac", smac_), ("dmac", dmac_)]]
            ]
        )

    def add_next_routing_simple(self, next_id, egress_port, smac, dmac):
        next_id_ = stringify(next_id, 4)
        egress_port_ = stringify(egress_port, 2)
        smac_ = mac_to_binary(smac)
        dmac_ = mac_to_binary(dmac)
        self.send_request_add_entry_to_action(
            "next.simple",
            [self.Exact("next_id", next_id_)],
            "next.routing_simple",
            [("port_num", egress_port_), ("smac", smac_), ("dmac", dmac_)])

    def add_next_vlan(self, next_id, new_vlan_id):
        next_id_ = stringify(next_id, 4)
        vlan_id_ = stringify(new_vlan_id, 2)
        self.send_request_add_entry_to_action(
            "pre_next.next_vlan",
            [self.Exact("next_id", next_id_)],
            "pre_next.set_vlan",
            [("vlan_id", vlan_id_)])

    def add_next_double_vlan(self, next_id, new_vlan_id, new_inner_vlan_id):
        next_id_ = stringify(next_id, 4)
        vlan_id_ = stringify(new_vlan_id, 2)
        inner_vlan_id_ = stringify(new_inner_vlan_id, 2)
        self.send_request_add_entry_to_action(
            "pre_next.next_vlan",
            [self.Exact("next_id", next_id_)],
            "pre_next.set_double_vlan",
            [("outer_vlan_id", vlan_id_),
             ("inner_vlan_id", inner_vlan_id_)])

    def add_next_hashed_indirect_action(self, next_id, action_name, params):
        next_id_ = stringify(next_id, 4)
        mbr_id = self.get_next_mbr_id()
        self.send_request_add_member("next.hashed_selector",
                                     mbr_id, action_name, params)
        self.send_request_add_entry_to_member(
            "next.hashed", [self.Exact("next_id", next_id_)], mbr_id)

    # actions is a tuple (action_name, param_tuples)
    # params_tuples contains a tuple for each param (param_name, param_value)
    def add_next_hashed_group_action(self, next_id, grp_id, actions=()):
        next_id_ = stringify(next_id, 4)
        mbr_ids = []
        for action in actions:
            mbr_id = self.get_next_mbr_id()
            mbr_ids.append(mbr_id)
            self.send_request_add_member("next.hashed_selector", mbr_id, *action)
        self.send_request_add_group("next.hashed_selector", grp_id,
                                    grp_size=len(mbr_ids), mbr_ids=mbr_ids)
        self.send_request_add_entry_to_group(
            "next.hashed",
            [self.Exact("next_id", next_id_)],
            grp_id)

    # next_hops is a list of tuples (egress_port, smac, dmac)
    def add_next_routing_group(self, next_id, grp_id, next_hops=None):
        actions = []
        if next_hops is not None:
            for (egress_port, smac, dmac) in next_hops:
                egress_port_ = stringify(egress_port, 2)
                smac_ = mac_to_binary(smac)
                dmac_ = mac_to_binary(dmac)
                actions.append([
                    "next.routing_hashed",
                    [("port_num", egress_port_), ("smac", smac_), ("dmac", dmac_)]
                ])
        self.add_next_hashed_group_action(next_id, grp_id, actions)

    def add_next_mpls(self, next_id, label):
        next_id_ = stringify(next_id, 4)
        label_ = stringify(label, 3)
        self.send_request_add_entry_to_action(
            "pre_next.next_mpls",
            [self.Exact("next_id", next_id_)],
            "pre_next.set_mpls_label",
            [("label", label_)])

    # next_hops is a list of tuples (egress_port, smac, dmac)
    def add_next_mpls_and_routing_group(self, next_id, grp_id, next_hops=None):
        actions = []
        if next_hops is not None:
            mpls_labels = list(map(lambda x: x[3], next_hops))
            if len(set(mpls_labels)) > 1:
                self.fail("More than one MPLS label passed to add_next_mpls_and_routing_group")
            self.add_next_mpls(next_id, mpls_labels[0])
            for (egress_port, smac, dmac, _) in next_hops:
                egress_port_ = stringify(egress_port, 2)
                smac_ = mac_to_binary(smac)
                dmac_ = mac_to_binary(dmac)
                actions.append([
                    "next.routing_hashed",
                    [("port_num", egress_port_), ("smac", smac_),
                     ("dmac", dmac_),]
                ])
        self.add_next_hashed_group_action(next_id, grp_id, actions)

    def add_mcast_group(self, group_id, ports):
        req = self.get_new_write_request()
        update = req.updates.add()
        update.type = p4runtime_pb2.Update.INSERT
        pre_entry = update.entity.packet_replication_engine_entry
        mg_entry = pre_entry.multicast_group_entry
        mg_entry.multicast_group_id = group_id
        for port in ports:
            replica = mg_entry.replicas.add()
            replica.egress_port = port
            replica.instance = 0
        return req, self.write_request(req)

    def add_clone_group(self, clone_id, ports):
        req = self.get_new_write_request()
        update = req.updates.add()
        update.type = p4runtime_pb2.Update.INSERT
        pre_entry = update.entity.packet_replication_engine_entry
        clone_entry = pre_entry.clone_session_entry
        clone_entry.session_id = clone_id
        clone_entry.class_of_service = 0
        clone_entry.packet_length_bytes = 0
        for port in ports:
            replica = clone_entry.replicas.add()
            replica.egress_port = port
            replica.instance = 1
        return req, self.write_request(req)


class BridgingTest(FabricTest):

    def runBridgingTest(self, tagged1, tagged2, pkt):
        vlan_id = 10
        mac_src = pkt[Ether].src
        mac_dst = pkt[Ether].dst
        self.setup_port(self.port1, vlan_id, PORT_TYPE_EDGE, tagged1)
        self.setup_port(self.port2, vlan_id, PORT_TYPE_EDGE, tagged2)
        # miss on filtering.fwd_classifier => bridging
        self.add_bridging_entry(vlan_id, mac_src, MAC_MASK, 10)
        self.add_bridging_entry(vlan_id, mac_dst, MAC_MASK, 20)
        self.add_next_output(10, self.port1)
        self.add_next_output(20, self.port2)

        exp_pkt = pkt.copy()
        pkt2 = pkt_mac_swap(pkt.copy())
        exp_pkt2 = pkt2.copy()
        if tagged1:
            pkt = pkt_add_vlan(pkt, vlan_vid=vlan_id)
            exp_pkt2 = pkt_add_vlan(exp_pkt2, vlan_vid=vlan_id)

        if tagged2:
            pkt2 = pkt_add_vlan(pkt2, vlan_vid=vlan_id)
            exp_pkt = pkt_add_vlan(exp_pkt, vlan_vid=vlan_id)

        self.send_packet(self.port1, str(pkt))
        self.send_packet(self.port2, str(pkt2))
        self.verify_each_packet_on_each_port([exp_pkt, exp_pkt2], [self.port2, self.port1])


class DoubleVlanXConnectTest(FabricTest):

    def runXConnectTest(self, pkt):
        vlan_id_outer = 100
        vlan_id_inner = 200
        next_id = 99

        self.setup_port(self.port1, vlan_id_outer, PORT_TYPE_EDGE, tagged=True)
        self.setup_port(self.port2, vlan_id_outer, PORT_TYPE_EDGE, tagged=True)
        # miss on filtering.fwd_classifier => bridging
        self.add_bridging_entry(vlan_id_outer, None, None, next_id)
        self.add_xconnect(next_id, self.port1, self.port2)

        pkt = pkt_add_vlan(pkt, vlan_vid=vlan_id_inner)
        pkt = pkt_add_vlan(pkt, vlan_vid=vlan_id_outer)
        exp_pkt = pkt.copy()

        self.send_packet(self.port1, str(pkt))
        self.verify_packet(exp_pkt, self.port2)

        self.send_packet(self.port2, str(pkt))
        self.verify_packet(exp_pkt, self.port1)


class ArpBroadcastTest(FabricTest):
    def runArpBroadcastTest(self, tagged_ports, untagged_ports):
        zero_mac_addr = ":".join(["00"] * 6)
        vlan_id = 10
        next_id = vlan_id
        mcast_group_id = vlan_id
        all_ports = tagged_ports + untagged_ports
        arp_pkt = testutils.simple_arp_packet(pktlen=MIN_PKT_LEN - 4)
        # Account for VLAN header size in total pktlen
        vlan_arp_pkt = testutils.simple_arp_packet(vlan_vid=vlan_id, pktlen=MIN_PKT_LEN)
        for port in tagged_ports:
            self.set_ingress_port_vlan(port, True, vlan_id, vlan_id)
        for port in untagged_ports:
            self.set_ingress_port_vlan(port, False, 0, vlan_id)
        self.add_bridging_entry(vlan_id, zero_mac_addr, zero_mac_addr, next_id)
        self.add_forwarding_acl_set_clone_session_id(eth_type=ETH_TYPE_ARP, clone_group_id=CPU_CLONE_SESSION_ID)
        self.add_next_multicast(next_id, mcast_group_id)
        # Add the multicast group
        self.add_mcast_group(mcast_group_id, all_ports)
        # Add the clone group
        self.add_clone_group(CPU_CLONE_SESSION_ID, [self.cpu_port])
        for port in tagged_ports:
            self.set_egress_vlan(port, vlan_id, True)
        for port in untagged_ports:
            self.set_egress_vlan(port, vlan_id, False)

        for inport in all_ports:
            pkt_to_send = vlan_arp_pkt if inport in tagged_ports else arp_pkt
            self.send_packet(inport, str(pkt_to_send))
            # Pkt should be received on CPU and on all ports, except the ingress one.
            self.verify_packet_in(exp_pkt=pkt_to_send, exp_in_port=inport)
            verify_tagged_ports = set(tagged_ports)
            verify_tagged_ports.discard(inport)
            for tport in verify_tagged_ports:
                self.verify_packet(vlan_arp_pkt, tport)
            verify_untagged_ports = set(untagged_ports)
            verify_untagged_ports.discard(inport)
            for uport in verify_untagged_ports:
                self.verify_packet(arp_pkt, uport)
        self.verify_no_other_packets()


class IPv4UnicastTest(FabricTest):

    def runIPv4UnicastTest(self, pkt, next_hop_mac,
                           tagged1=False, tagged2=False, prefix_len=24,
                           exp_pkt=None, exp_pkt_base=None, next_id=None,
                           next_vlan=None, mpls=False, dst_ipv4=None,
                           routed_eth_types=(ETH_TYPE_IPV4,),
                           verify_pkt=True, from_packet_out=False,
                           override_eg_port=None,
                           port_type1=PORT_TYPE_EDGE,
                           port_type2=PORT_TYPE_EDGE,):
        """
        Execute an IPv4 unicast routing test.
        :param pkt: input packet
        :param next_hop_mac: MAC address of the next hop
        :param tagged1: if the input port should expect VLAN tagged packets
        :param tagged2: if the output port should expect VLAN tagged packets
        :param prefix_len: prefix length to use in the routing table
        :param exp_pkt: expected packet, if none one will be built using the
            input packet
        :param exp_pkt_base: if not none, it will be used to build the expected
            output packet.
        :param next_id: value to use as next ID
        :param next_vlan: value to use as next VLAN
        :param mpls: whether the packet should be routed to the spines using
            MPLS SR
        :param dst_ipv4: if not none, this value will be used as IPv4 dst to
            configure tables
        :param routed_eth_types: eth type values used to configure the
            classifier table to process packets via routing
        :param verify_pkt: whether packets are expected to be forwarded or
            dropped
        :param from_packet_out: ingress packet is a packet-out (enables do_forwarding)
        :param override_eg_port: to override the default or the provided eg port
        :param port_type1: port type to be used for the programming of the ig port
        :param port_type2: port type to be used for the programming of the eg port
        """
        if IP not in pkt or Ether not in pkt:
            self.fail("Cannot do IPv4 test with packet that is not IP")
        if mpls and tagged2:
            self.fail("Cannot do MPLS test with egress port tagged (tagged2)")

        if from_packet_out:
            ig_port = self.cpu_port
        else:
            ig_port = self.port1
        eg_port = self.port2

        # If the input pkt has a VLAN tag, use that to configure tables.
        pkt_is_tagged = False
        if Dot1Q in pkt:
            vlan1 = pkt[Dot1Q].vlan
            tagged1 = True
            pkt_is_tagged = True
            # packet-outs should arrive be untagged
            assert not from_packet_out
        else:
            vlan1 = VLAN_ID_1

        if mpls:
            # If MPLS test, port2 is assumed to be a spine port, with
            # default vlan untagged.
            vlan2 = DEFAULT_VLAN
            assert not tagged2
        else:
            vlan2 = VLAN_ID_2 if next_vlan is None else next_vlan

        next_id = 100 if next_id is None else next_id
        group_id = next_id
        mpls_label = MPLS_LABEL_2
        if dst_ipv4 is None:
            dst_ipv4 = pkt[IP].dst
        if from_packet_out:
            switch_mac = SWITCH_MAC
        else:
            switch_mac = pkt[Ether].dst

        # Setup ports.
        self.setup_port(ig_port, vlan1, port_type1, tagged1)
        self.setup_port(eg_port, vlan2, port_type2, tagged2)

        # Forwarding type -> routing v4
        for eth_type in routed_eth_types:
            self.set_forwarding_type(
                ig_port,
                switch_mac if not from_packet_out else None,
                eth_type,
                FORWARDING_TYPE_UNICAST_IPV4)

        # Routing entry.
        self.add_forwarding_routing_v4_entry(dst_ipv4, prefix_len, next_id)

        if not mpls:
            self.add_next_routing(next_id, eg_port, switch_mac, next_hop_mac)
            self.add_next_vlan(next_id, vlan2)
        else:
            params = [eg_port, switch_mac, next_hop_mac, mpls_label]
            self.add_next_mpls_and_routing_group(next_id, group_id, [params])
            self.add_next_vlan(next_id, DEFAULT_VLAN)

        if exp_pkt is None:
            # Build exp pkt using the input one.
            exp_pkt = pkt.copy() if not exp_pkt_base else exp_pkt_base
            # Route
            exp_pkt[Ether].src = switch_mac
            exp_pkt[Ether].dst = next_hop_mac
            if not mpls:
                exp_pkt = pkt_decrement_ttl(exp_pkt)
            if tagged2 and Dot1Q not in exp_pkt:
                exp_pkt = pkt_add_vlan(exp_pkt, vlan_vid=vlan2)
            if mpls:
                exp_pkt = pkt_add_mpls(exp_pkt, label=mpls_label,
                                       ttl=DEFAULT_MPLS_TTL)

        if tagged1 and not pkt_is_tagged:
            pkt = pkt_add_vlan(pkt, vlan_vid=vlan1)

        if from_packet_out:
            self.send_packet_out(self.build_packet_out(
                pkt, port=0, do_forwarding=True))
        else:
            self.send_packet(ig_port, str(pkt))

        verify_port = eg_port
        if override_eg_port:
            verify_port = override_eg_port

        if verify_pkt:
            self.verify_packet(exp_pkt, verify_port)
        self.verify_no_other_packets()


class DoubleVlanTerminationTest(FabricTest):

    def runRouteAndPushTest(self, pkt, next_hop_mac,
                            prefix_len=24,
                            exp_pkt=None,
                            next_id=None,
                            next_vlan_id=None,
                            next_inner_vlan_id=None,
                            in_tagged=False,
                            dst_ipv4=None,
                            routed_eth_types=(ETH_TYPE_IPV4,),
                            verify_pkt=True):
        """
        Route and Push test case. The switch output port is expected to send double tagged packets.
        The switch routes the packet to the correct destination and adds the double VLAN tag to it.
        :param pkt:
        :param next_hop_mac:
        :param prefix_len:
        :param exp_pkt:
        :param next_id:
        :param next_vlan_id:
        :param next_inner_vlan_id:
        :param in_tagged:
        :param dst_ipv4:
        :param routed_eth_types:
        :param verify_pkt:
        :return:
        """

        if IP not in pkt or Ether not in pkt:
            self.fail("Cannot do IPv4 test with packet that is not IP")

        pkt_is_tagged = False
        if Dot1Q in pkt:
            in_vlan = pkt[Dot1Q].vlan
            in_tagged = True
            pkt_is_tagged = True
        else:
            in_vlan = VLAN_ID_3

        next_id = 100 if next_id is None else next_id

        if dst_ipv4 is None:
            dst_ipv4 = pkt[IP].dst
        switch_mac = pkt[Ether].dst

        # Setup port 1
        self.setup_port(self.port1, vlan_id=in_vlan, port_type=PORT_TYPE_INFRA, tagged=in_tagged)
        # Setup port 2: packets on this port are double tagged packets
        self.setup_port(self.port2, vlan_id=next_vlan_id, port_type=PORT_TYPE_INFRA, double_tagged=True, inner_vlan_id=next_inner_vlan_id)

        # Forwarding type -> routing v4
        for eth_type in routed_eth_types:
            self.set_forwarding_type(self.port1, switch_mac, eth_type,
                                     FORWARDING_TYPE_UNICAST_IPV4)

        # Routing entry.
        self.add_forwarding_routing_v4_entry(dst_ipv4, prefix_len, next_id)
        self.add_next_routing(next_id, self.port2, switch_mac, next_hop_mac)

        # Push double vlan
        self.add_next_double_vlan(next_id, next_vlan_id, next_inner_vlan_id)

        if exp_pkt is None:
            # Build exp pkt using the input one.
            exp_pkt = pkt.copy()
            if in_tagged and pkt_is_tagged:
                exp_pkt = pkt_remove_vlan(exp_pkt, in_vlan)
            exp_pkt = pkt_add_vlan(exp_pkt, next_vlan_id)
            exp_pkt = pkt_add_inner_vlan(exp_pkt, next_inner_vlan_id)
            exp_pkt = pkt_route(exp_pkt, next_hop_mac)
            exp_pkt = pkt_decrement_ttl(exp_pkt)

        if in_tagged and not pkt_is_tagged:
            pkt = pkt_add_vlan(pkt, vlan_vid=in_vlan)

        testutils.send_packet(self, self.port1, str(pkt))
        if verify_pkt:
            testutils.verify_packet(self, exp_pkt, self.port2)
        self.verify_no_other_packets()

    def runPopAndRouteTest(self, pkt, next_hop_mac,
                           prefix_len=24,
                           exp_pkt=None,
                           next_id=None,
                           vlan_id=None,
                           inner_vlan_id=None,
                           out_tagged=False,
                           mpls=False,
                           dst_ipv4=None,
                           routed_eth_types=(ETH_TYPE_IPV4,),
                           verify_pkt=True):
        """
        Pop and Route test case. The switch port expect to receive double tagged packets.
        The switch removes both VLAN headers from the packet and routes it to the correct destination.
        :param pkt:
        :param next_hop_mac:
        :param prefix_len:
        :param exp_pkt:
        :param next_id:
        :param vlan_id:
        :param inner_vlan_id:
        :param out_tagged:
        :param mpls:
        :param dst_ipv4:
        :param routed_eth_types:
        :param verify_pkt:
        :return:
        """

        if IP not in pkt or Ether not in pkt:
            self.fail("Cannot do IPv4 test with packet that is not IP")
        if mpls and out_tagged:
            self.fail("Cannot do MPLS test with egress port tagged (out_tagged)")

        if Dot1Q not in pkt:
            pkt = pkt_add_vlan(pkt, vlan_vid=vlan_id)
            pkt = pkt_add_inner_vlan(pkt, vlan_vid=inner_vlan_id)
        else:
            try:
                pkt[Dot1Q:2]
            except IndexError:
                # Add the not added vlan header
                if pkt[Dot1Q:1].vlan == vlan_id:
                    pkt = pkt_add_inner_vlan(pkt, vlan_vid=inner_vlan_id)
                elif pkt[Dot1Q:1].vlan == inner_vlan_id:
                    pkt = pkt_add_vlan(pkt, vlan_vid=vlan_id)
                else:
                    self.fail("Packet should be without VLANs or with correct VLANs")
        if mpls:
            # If MPLS test, egress_port is assumed to be a spine port, with
            # default vlan untagged.
            next_vlan = DEFAULT_VLAN
            assert not out_tagged
        else:
            next_vlan = VLAN_ID_3 if out_tagged else vlan_id
        next_id = 100 if next_id is None else next_id
        group_id = next_id
        mpls_label = MPLS_LABEL_2

        if dst_ipv4 is None:
            dst_ipv4 = pkt[IP].dst
        switch_mac = pkt[Ether].dst

        # Setup port 1: packets on this port are double tagged packets
        self.setup_port(self.port1, vlan_id=vlan_id, port_type=PORT_TYPE_INFRA, double_tagged=True, inner_vlan_id=inner_vlan_id)
        # Setup port 2
        self.setup_port(self.port2, vlan_id=next_vlan, port_type=PORT_TYPE_INFRA, tagged=out_tagged)

        # Forwarding type -> routing v4
        for eth_type in routed_eth_types:
            self.set_forwarding_type(self.port1, switch_mac, eth_type,
                                     FORWARDING_TYPE_UNICAST_IPV4)
        self.add_forwarding_routing_v4_entry(dst_ipv4, prefix_len, next_id)

        if not mpls:
            self.add_next_routing(next_id, self.port2, switch_mac, next_hop_mac)
            self.add_next_vlan(next_id, next_vlan)
        else:
            params = [self.port2, switch_mac, next_hop_mac, mpls_label]
            self.add_next_mpls_and_routing_group(next_id, group_id, [params])
            self.add_next_vlan(next_id, DEFAULT_VLAN)

        if exp_pkt is None:
            # Build exp pkt using the input one.
            exp_pkt = pkt.copy()
            exp_pkt = pkt_route(exp_pkt, next_hop_mac)
            exp_pkt = pkt_remove_vlan(exp_pkt)
            exp_pkt = pkt_remove_vlan(exp_pkt)
            if not mpls:
                exp_pkt = pkt_decrement_ttl(exp_pkt)
            if out_tagged and Dot1Q not in exp_pkt:
                exp_pkt = pkt_add_vlan(exp_pkt, vlan_vid=next_vlan)
            if mpls:
                exp_pkt = pkt_add_mpls(exp_pkt, label=mpls_label,
                                       ttl=DEFAULT_MPLS_TTL)

        testutils.send_packet(self, self.port1, str(pkt))
        if verify_pkt:
            testutils.verify_packet(self, exp_pkt, self.port2)
        self.verify_no_other_packets()


class MplsSegmentRoutingTest(FabricTest):
    def runMplsSegmentRoutingTest(self, pkt, dst_mac, next_hop_spine=True):
        if IP not in pkt or Ether not in pkt:
            self.fail("Cannot do MPLS segment routing test with packet that is not IP")
        if Dot1Q in pkt:
            self.fail("Cannot do MPLS segment routing test with VLAN tagged packet")

        next_id = MPLS_LABEL_1
        label = MPLS_LABEL_1
        group_id = MPLS_LABEL_1
        mpls_ttl = DEFAULT_MPLS_TTL
        switch_mac = pkt[Ether].dst

        # Setup ports, both untagged
        self.setup_port(self.port1, DEFAULT_VLAN, PORT_TYPE_INFRA, False)
        self.setup_port(self.port2, DEFAULT_VLAN, PORT_TYPE_INFRA, False)
        # Forwarding type -> mpls
        self.set_forwarding_type(self.port1, switch_mac, ETH_TYPE_MPLS_UNICAST,
                                 FORWARDING_TYPE_MPLS)
        # Mpls entry.
        self.add_forwarding_mpls_entry(label, next_id)

        if not next_hop_spine:
            self.add_next_routing(next_id, self.port2, switch_mac, dst_mac)
        else:
            params = [self.port2, switch_mac, dst_mac, label]
            self.add_next_mpls_and_routing_group(next_id, group_id, [params])

        exp_pkt = pkt.copy()
        pkt = pkt_add_mpls(pkt, label, mpls_ttl)
        exp_pkt[Ether].src = switch_mac
        exp_pkt[Ether].dst = dst_mac
        if not next_hop_spine:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        else:
            exp_pkt = pkt_add_mpls(exp_pkt, label, mpls_ttl - 1)

        self.send_packet(self.port1, str(pkt))
        self.verify_packet(exp_pkt, self.port2)


class PacketOutTest(FabricTest):
    def runPacketOutTest(self, pkt):
        for port in [self.port1, self.port2]:
            self.verify_packet_out(pkt, out_port=port)
        self.verify_no_other_packets()


class PacketInTest(FabricTest):
    def runPacketInTest(self, pkt, eth_type, tagged=False, vlan_id=10):
        self.add_forwarding_acl_punt_to_cpu(eth_type=eth_type)
        for port in [self.port1, self.port2]:
            if tagged:
                self.set_ingress_port_vlan(port, True, vlan_id, vlan_id)
            else:
                self.set_ingress_port_vlan(port, False, 0, vlan_id)
            self.send_packet(port, str(pkt))
            self.verify_packet_in(pkt, port)
        self.verify_no_other_packets()


class SpgwSimpleTest(IPv4UnicastTest):

    def read_pkt_count(self, c_name, idx):
        counter = self.read_counter(c_name, idx, typ="PACKETS")
        return counter.data.packet_count

    def read_byte_count(self, c_name, idx):
        counter = self.read_counter(c_name, idx, typ="BYTES")
        return counter.data.byte_count

    def _add_spgw_iface(self, iface_addr, prefix_len, iface_enum, dir_enum, gtpu_valid):
        req = self.get_new_write_request()

        _iface_addr = ipv4_to_binary(iface_addr)

        self.push_update_add_entry_to_action(
            req,
            "FabricIngress.spgw.interfaces",
            [
                self.Lpm("ipv4_dst_addr", _iface_addr, prefix_len),
                self.Exact("gtpu_is_valid", stringify(int(gtpu_valid), 1))
            ],
            "FabricIngress.spgw.load_iface",
            [
                ("src_iface", stringify(iface_enum, 1))
            ],
        )
        self.write_request(req)

    def add_ue_pool(self, pool_addr, prefix_len=32):
        self._add_spgw_iface(
                iface_addr=pool_addr,
                prefix_len=prefix_len,
                iface_enum=SPGW_IFACE_CORE,
                dir_enum=SPGW_DIRECTION_DOWNLINK,
                gtpu_valid=False)

    def add_s1u_iface(self, s1u_addr, prefix_len=32):
        self._add_spgw_iface(
                iface_addr=s1u_addr,
                prefix_len=prefix_len,
                iface_enum=SPGW_IFACE_ACCESS,
                dir_enum=SPGW_DIRECTION_DOWNLINK,
                gtpu_valid=True)

    def add_dbuf_device(self,
                        dbuf_addr=DBUF_IPV4, drain_dst_addr=DBUF_DRAIN_DST_IPV4,
                        dbuf_far_id=DBUF_FAR_ID, dbuf_teid=DBUF_TEID):
        # Switch interface for traffic to/from dbuf device
        self._add_spgw_iface(
                iface_addr=drain_dst_addr,
                prefix_len=32,
                iface_enum=SPGW_IFACE_FROM_DBUF,
                dir_enum=SPGW_DIRECTION_DOWNLINK,
                gtpu_valid=True)

        # FAR that tunnels to the dbuf device
        return self._add_far(
            dbuf_far_id,
            "FabricIngress.spgw.load_dbuf_far",
            [
                ("drop", stringify(0, 1)),
                ("notify_cp", stringify(0, 1)),
                ("teid", stringify(dbuf_teid, 4)),
                ("tunnel_src_port", stringify(UDP_GTP_PORT, 2)),
                ("tunnel_src_addr", ipv4_to_binary(drain_dst_addr)),
                ("tunnel_dst_addr", ipv4_to_binary(dbuf_addr)),
            ]
        )

    def add_uplink_pdr(self, ctr_id, far_id,
                        teid, tunnel_dst_addr):
        req = self.get_new_write_request()
        self.push_update_add_entry_to_action(
            req,
            "FabricIngress.spgw.uplink_pdrs",
            [
                self.Exact("teid", stringify(teid, 4)),
                self.Exact("tunnel_ipv4_dst", ipv4_to_binary(tunnel_dst_addr)),
            ],
            "FabricIngress.spgw.load_pdr",
            [
                ("ctr_id", stringify(ctr_id, 4)),
                ("far_id", stringify(far_id, 4)),
                ("needs_gtpu_decap", stringify(1, 1))
            ],
        )
        self.write_request(req)

    def add_downlink_pdr(self, ctr_id, far_id, ue_addr):
        req = self.get_new_write_request()

        self.push_update_add_entry_to_action(
            req,
            "FabricIngress.spgw.downlink_pdrs",
            [self.Exact("ue_addr", ipv4_to_binary(ue_addr))],
            "FabricIngress.spgw.load_pdr",
            [
                ("ctr_id", stringify(ctr_id, 4)),
                ("far_id", stringify(far_id, 4)),
                ("needs_gtpu_decap", stringify(0, 1))
            ],
        )
        self.write_request(req)

    def _add_far(self, far_id, action_name, action_params):
        req = self.get_new_write_request()
        self.push_update_add_entry_to_action(
            req,
            "FabricIngress.spgw.fars",
            [self.Exact("far_id", stringify(far_id, 4))],
            action_name,
            action_params,
        )
        self.write_request(req)

    def add_normal_far(self, far_id, drop=False, notify_cp=False):
        return self._add_far(
            far_id,
            "FabricIngress.spgw.load_normal_far",
            [
                ("drop", stringify(drop, 1)),
                ("notify_cp", stringify(notify_cp, 1)),
            ]
        )

    def add_tunnel_far(self, far_id, teid, tunnel_src_addr, tunnel_dst_addr,
                       tunnel_src_port=DEFAULT_GTP_TUNNEL_SPORT, drop=False, notify_cp=False):
        return self._add_far(
            far_id,
            "FabricIngress.spgw.load_tunnel_far",
            [
                ("drop", stringify(drop, 1)),
                ("notify_cp", stringify(notify_cp, 1)),
                ("tunnel_src_port", stringify(tunnel_src_port, 2)),
                ("teid", stringify(teid, 4)),
                ("tunnel_src_addr", ipv4_to_binary(tunnel_src_addr)),
                ("tunnel_dst_addr", ipv4_to_binary(tunnel_dst_addr)),
            ]
        )

    def setup_uplink(self, s1u_sgw_addr, teid, ctr_id, far_id=None):
        if far_id is None:
            far_id = 23  # 23 is the most random number less than 100

        self.add_s1u_iface(s1u_sgw_addr)
        self.add_uplink_pdr(
            ctr_id=ctr_id,
            far_id=far_id,
            teid=teid,
            tunnel_dst_addr=s1u_sgw_addr)
        self.add_normal_far(far_id=far_id)

    def setup_downlink(self, s1u_sgw_addr, s1u_enb_addr, teid, ue_addr, ctr_id, far_id=None):
        if far_id is None:
            far_id = 24  # the second most random  number

        self.add_ue_pool(ue_addr)
        self.add_downlink_pdr(ctr_id=ctr_id, far_id=far_id, ue_addr=ue_addr)
        self.add_tunnel_far(
            far_id=far_id,
            teid=teid,
            tunnel_src_addr=s1u_sgw_addr,
            tunnel_dst_addr=s1u_enb_addr)

    def read_pdr_counters(self, ctr_id):
        ingress_ctr = self.read_pkt_count("FabricIngress.spgw.pdr_counter", ctr_id)
        egress_ctr = self.read_pkt_count("FabricEgress.spgw.pdr_counter", ctr_id)
        return (ingress_ctr, egress_ctr)

    def check_pdr_counters_increased(self, ctr_id, count_tuple,
                                     exp_ingress_inc=1, exp_egress_inc=1):
        ingress_ctr = self.read_pkt_count("FabricIngress.spgw.pdr_counter", ctr_id)
        egress_ctr = self.read_pkt_count("FabricEgress.spgw.pdr_counter", ctr_id)

        ingress_inc = ingress_ctr - count_tuple[0]
        egress_inc = egress_ctr - count_tuple[1]

        if ingress_inc != exp_ingress_inc:
            self.fail("Ingress PDR packet counter incremented by %d instead of $d!" % (ingress_inc, exp_ingress_inc))
        if egress_inc != exp_egress_inc:
            self.fail("Egress PDR packet counter incremented by %d instead of %d!" % (egress_inc, exp_egress_inc))

    def runUplinkTest(self, ue_out_pkt, tagged1, tagged2, mpls):
        ctr_id = 1
        dst_mac = HOST2_MAC

        gtp_pkt = pkt_add_gtp(ue_out_pkt, out_ipv4_src=S1U_ENB_IPV4,
                              out_ipv4_dst=S1U_SGW_IPV4, teid=TEID_1)
        exp_pkt = ue_out_pkt.copy()
        exp_pkt[Ether].src = exp_pkt[Ether].dst
        exp_pkt[Ether].dst = dst_mac
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        else:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)
        if tagged2:
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        self.setup_uplink(
            s1u_sgw_addr=S1U_SGW_IPV4,
            teid=TEID_1,
            ctr_id=ctr_id
        )

        ingress_pdr_pkt_ctr1 = self.read_pkt_count("FabricIngress.spgw.pdr_counter", ctr_id)

        self.runIPv4UnicastTest(pkt=gtp_pkt, dst_ipv4=ue_out_pkt[IP].dst,
                                next_hop_mac=dst_mac,
                                prefix_len=32, exp_pkt=exp_pkt,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls)

        # Verify the PDR packet counter increased
        ingress_pdr_pkt_ctr2 = self.read_pkt_count("FabricIngress.spgw.pdr_counter", ctr_id)
        ctr_increase = ingress_pdr_pkt_ctr2 - ingress_pdr_pkt_ctr1
        if ctr_increase != 1:
            self.fail("PDR packet counter incremented by %d instead of 1!" % ctr_increase)

    def runUplinkTest(self, ue_out_pkt, tagged1, tagged2, mpls):
        upstream_mac = HOST2_MAC

        gtp_pkt = pkt_add_gtp(ue_out_pkt, out_ipv4_src=S1U_ENB_IPV4,
                              out_ipv4_dst=S1U_SGW_IPV4, teid=UPLINK_TEID)
        gtp_pkt[Ether].src = S1U_ENB_MAC
        gtp_pkt[Ether].dst = SWITCH_MAC

        exp_pkt = ue_out_pkt.copy()
        exp_pkt[Ether].src = SWITCH_MAC
        exp_pkt[Ether].dst = upstream_mac
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        else:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)
        if tagged2:
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        self.setup_uplink(
            s1u_sgw_addr=S1U_SGW_IPV4,
            teid=UPLINK_TEID,
            ctr_id=UPLINK_PDR_CTR_ID
        )

        # Read SPGW counters before sending the packet
        pdr_pkt_counts = self.read_pdr_counters(UPLINK_PDR_CTR_ID)

        self.runIPv4UnicastTest(pkt=gtp_pkt, dst_ipv4=ue_out_pkt[IP].dst,
                                next_hop_mac=upstream_mac,
                                prefix_len=32, exp_pkt=exp_pkt,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls)

        # Verify the Ingress and Egress PDR counters increased
        self.check_pdr_counters_increased(UPLINK_PDR_CTR_ID, pdr_pkt_counts)

    def runDownlinkTest(self, pkt, tagged1, tagged2, mpls):
        exp_pkt = pkt.copy()
        exp_pkt[Ether].src = SWITCH_MAC
        exp_pkt[Ether].dst = S1U_ENB_MAC
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        exp_pkt = pkt_add_gtp(exp_pkt, out_ipv4_src=S1U_SGW_IPV4,
                              out_ipv4_dst=S1U_ENB_IPV4, teid=DOWNLINK_TEID)
        if mpls:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)
        if tagged2:
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        self.setup_downlink(
            s1u_sgw_addr=S1U_SGW_IPV4,
            s1u_enb_addr=S1U_ENB_IPV4,
            teid=DOWNLINK_TEID,
            ue_addr=UE_IPV4,
            ctr_id=DOWNLINK_PDR_CTR_ID,
        )

        # Read SPGW counters before sending the packet
        pdr_pkt_counts = self.read_pdr_counters(DOWNLINK_PDR_CTR_ID)

        self.runIPv4UnicastTest(pkt=pkt, dst_ipv4=exp_pkt[IP].dst,
                                next_hop_mac=S1U_ENB_MAC,
                                prefix_len=32, exp_pkt=exp_pkt,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls)

        # Verify the Ingress and Egress PDR counters increased
        self.check_pdr_counters_increased(DOWNLINK_PDR_CTR_ID, pdr_pkt_counts)

    def runDownlinkToDbufTest(self, pkt, tagged1, tagged2, mpls):
        exp_pkt = pkt.copy()
        exp_pkt[Ether].src = SWITCH_MAC
        exp_pkt[Ether].dst = DBUF_MAC
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        # add dbuf tunnel
        exp_pkt = pkt_add_gtp(exp_pkt, out_ipv4_src=DBUF_DRAIN_DST_IPV4,
                              out_ipv4_dst=DBUF_IPV4, teid=DBUF_TEID,
                              sport=UDP_GTP_PORT)
        if mpls:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)
        if tagged2:
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        # Add the UE pool interface and the PDR pointing to the DBUF FAR
        self.add_ue_pool(UE_IPV4)
        self.add_downlink_pdr(ctr_id=DOWNLINK_PDR_CTR_ID, far_id=DBUF_FAR_ID, ue_addr=UE_IPV4)

        # Add rules for sending/receiving packets to/from dbuf
        # (receiving isn't done by this test though)
        self.add_dbuf_device(dbuf_addr=DBUF_IPV4, drain_dst_addr=DBUF_DRAIN_DST_IPV4,
                             dbuf_far_id=DBUF_FAR_ID, dbuf_teid=DBUF_TEID)

        # Read SPGW counters before sending the packet
        pdr_pkt_counts = self.read_pdr_counters(DOWNLINK_PDR_CTR_ID)

        self.runIPv4UnicastTest(pkt=pkt, dst_ipv4=exp_pkt[IP].dst,
                                next_hop_mac=DBUF_MAC,
                                prefix_len=32, exp_pkt=exp_pkt,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls)

        # Verify the Ingress PDR packet counter increased, but the egress did not
        self.check_pdr_counters_increased(DOWNLINK_PDR_CTR_ID, pdr_pkt_counts, exp_egress_inc=0)

    def runDownlinkFromDbufTest(self, pkt, tagged1, tagged2, mpls):
        """ Tests a packet returning from dbuf to be sent to the enodeb.
            Similar to a normal downlink test, but the input is gtpu encapped.
        """
        # The input packet is from dbuf and is GTP encapsulated
        pkt_from_dbuf = pkt.copy()
        pkt_from_dbuf[Ether].src = DBUF_MAC
        pkt_from_dbuf[Ether].dst = SWITCH_MAC
        pkt_from_dbuf = pkt_add_gtp(pkt_from_dbuf, out_ipv4_src=DBUF_IPV4,
                                    out_ipv4_dst=DBUF_DRAIN_DST_IPV4, teid=DBUF_TEID)

        # A normal downlink packet to the enodeb is the expected output
        exp_pkt = pkt.copy()
        exp_pkt[Ether].src = SWITCH_MAC
        exp_pkt[Ether].dst = S1U_ENB_MAC
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        exp_pkt = pkt_add_gtp(exp_pkt, out_ipv4_src=S1U_SGW_IPV4,
                              out_ipv4_dst=S1U_ENB_IPV4, teid=DOWNLINK_TEID)
        if mpls:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)
        if tagged2:
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        # Normal downlink rules
        self.setup_downlink(
            s1u_sgw_addr=S1U_SGW_IPV4,
            s1u_enb_addr=S1U_ENB_IPV4,
            teid=DOWNLINK_TEID,
            ue_addr=UE_IPV4,
            ctr_id=DOWNLINK_PDR_CTR_ID,
        )

        # Add rules for sending/receiving packets to/from dbuf
        # (sending isn't done by this test though)
        self.add_dbuf_device(dbuf_addr=DBUF_IPV4, drain_dst_addr=DBUF_DRAIN_DST_IPV4,
                             dbuf_far_id=DBUF_FAR_ID, dbuf_teid=DBUF_TEID)

        # Read SPGW counters before sending the packet
        pdr_pkt_counts = self.read_pdr_counters(DOWNLINK_PDR_CTR_ID)

        self.runIPv4UnicastTest(pkt=pkt_from_dbuf, dst_ipv4=exp_pkt[IP].dst,
                                next_hop_mac=S1U_ENB_MAC,
                                prefix_len=32, exp_pkt=exp_pkt,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls)

        # Verify the Ingress PDR packet counter did not increase, but the egress did
        self.check_pdr_counters_increased(DOWNLINK_PDR_CTR_ID, pdr_pkt_counts, exp_ingress_inc=0)


class IntTest(IPv4UnicastTest):
    def setup_transit(self, switch_id):
        self.send_request_add_entry_to_action(
            "tb_int_insert",
            [self.Exact("int_is_valid", stringify(1, 1))],
            "init_metadata", [("switch_id", stringify(switch_id, 4))])

    def setup_source_port(self, source_port):
        source_port_ = stringify(source_port, 2)
        self.send_request_add_entry_to_action(
            "tb_set_source",
            [self.Exact("ig_port", source_port_)],
            "int_set_source", [])

    def get_ins_mask(self, instructions):
        return reduce(ior, instructions)

    def get_ins_from_mask(self, ins_mask):
        instructions = []
        for i in range(16):
            ins = ins_mask & (1 << i)
            if ins:
                instructions.append(ins)
        return instructions

    def get_int_pkt(self, pkt, instructions, max_hop, transit_hops=0, hop_metadata=None):
        proto = UDP if UDP in pkt else TCP
        int_pkt = pkt.copy()
        int_pkt[IP].tos = 0x04
        shim_len = 4 + len(instructions) * transit_hops
        int_shim = INT_L45_HEAD(int_type=1, length=shim_len)
        int_header = INT_META_HDR(
            ins_cnt=len(instructions),
            max_hop_cnt=max_hop,
            total_hop_cnt=transit_hops,
            inst_mask=self.get_ins_mask(instructions))
        int_tail = INT_L45_TAIL(next_proto=pkt[IP].proto, proto_param=pkt[proto].dport)
        metadata = "".join([hop_metadata] * transit_hops)
        int_payload = int_shim / int_header / metadata / int_tail
        int_pkt[proto].payload = int_payload / int_pkt[proto].payload
        return int_pkt

    def get_int_metadata(self, instructions, switch_id, ig_port, eg_port):
        int_metadata = ""
        masked_ins_cnt = len(instructions)
        if INT_SWITCH_ID in instructions:
            int_metadata += stringify(switch_id, 4)
            masked_ins_cnt -= 1
        if INT_IG_EG_PORT in instructions:
            int_metadata += stringify(ig_port, 2) + stringify(eg_port, 2)
            masked_ins_cnt -= 1
        int_metadata += "".join(["\x00\x00\x00\x00"] * masked_ins_cnt)
        return int_metadata, masked_ins_cnt

    def setup_source_flow(self, ipv4_src, ipv4_dst, sport, dport, instructions, max_hop):
        ipv4_src_ = ipv4_to_binary(ipv4_src)
        ipv4_dst_ = ipv4_to_binary(ipv4_dst)
        ipv4_mask = ipv4_to_binary("255.255.255.255")
        sport_ = stringify(sport, 2)
        dport_ = stringify(dport, 2)
        port_mask = stringify(65535, 2)

        instructions = set(instructions)
        ins_mask = self.get_ins_mask(instructions)
        ins_cnt = len(instructions)
        ins_mask0407 = (ins_mask >> 8) & 0xF
        ins_mask0003 = ins_mask >> 12

        max_hop_ = stringify(max_hop, 1)
        ins_cnt_ = stringify(ins_cnt, 1)
        ins_mask0003_ = stringify(ins_mask0003, 1)
        ins_mask0407_ = stringify(ins_mask0407, 1)

        self.send_request_add_entry_to_action(
            "tb_int_source",
            [self.Ternary("ipv4_src", ipv4_src_, ipv4_mask),
             self.Ternary("ipv4_dst", ipv4_dst_, ipv4_mask),
             self.Ternary("l4_sport", sport_, port_mask),
             self.Ternary("l4_dport", dport_, port_mask),
             ],
            "int_source_dscp", [
                ("max_hop", max_hop_),
                ("ins_cnt", ins_cnt_),
                ("ins_mask0003", ins_mask0003_),
                ("ins_mask0407", ins_mask0407_)
            ], priority=DEFAULT_PRIORITY)

    def runIntSourceTest(self, pkt, tagged1, tagged2, instructions,
                         with_transit=True, ignore_csum=False, switch_id=1,
                         max_hop=5, mpls=False):
        if IP not in pkt:
            self.fail("Packet is not IP")
        if UDP not in pkt and TCP not in pkt:
            self.fail("Packet must be UDP or TCP for INT tests")
        proto = UDP if UDP in pkt else TCP

        # will use runIPv4UnicastTest
        dst_mac = HOST2_MAC
        ig_port = self.port1
        eg_port = self.port2

        ipv4_src = pkt[IP].src
        ipv4_dst = pkt[IP].dst
        sport = pkt[proto].sport
        dport = pkt[proto].dport

        instructions = set(instructions)
        ins_cnt = len(instructions)

        self.setup_source_port(ig_port)
        self.setup_source_flow(
            ipv4_src=ipv4_src, ipv4_dst=ipv4_dst, sport=sport, dport=dport,
            instructions=instructions, max_hop=max_hop)
        if with_transit:
            self.setup_transit(switch_id)

        if with_transit:
            int_metadata, masked_ins_cnt = self.get_int_metadata(
                instructions=instructions, switch_id=switch_id,
                ig_port=ig_port, eg_port=eg_port)
        else:
            int_metadata, masked_ins_cnt = "", ins_cnt

        exp_pkt = self.get_int_pkt(
            pkt=pkt, instructions=instructions, max_hop=max_hop,
            transit_hops=1 if with_transit else 0,
            hop_metadata=int_metadata)

        exp_pkt[Ether].src = exp_pkt[Ether].dst
        exp_pkt[Ether].dst = dst_mac
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        else:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)

        if tagged2:
            # VLAN if tagged1 will be added by runIPv4UnicastTest
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        if with_transit or ignore_csum:
            mask_pkt = Mask(exp_pkt)
            if with_transit:
                offset_metadata = len(exp_pkt) - len(exp_pkt[proto].payload) \
                                  + len(INT_L45_HEAD()) + len(INT_META_HDR()) \
                                  + (ins_cnt - masked_ins_cnt) * 4
                mask_pkt.set_do_not_care(offset_metadata * 8, masked_ins_cnt * 4 * 8)
            if ignore_csum:
                csum_offset = len(exp_pkt) - len(exp_pkt[IP].payload) \
                              + (6 if proto is UDP else 16)
                mask_pkt.set_do_not_care(csum_offset * 8, 2 * 8)
            exp_pkt = mask_pkt

        self.runIPv4UnicastTest(pkt=pkt, next_hop_mac=HOST2_MAC, prefix_len=32,
                                exp_pkt=exp_pkt,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls)

    def runIntTransitTest(self, pkt, tagged1, tagged2,
                          ignore_csum=False, switch_id=1, mpls=False):
        if IP not in pkt:
            self.fail("Packet is not IP")
        if UDP not in pkt and TCP not in pkt:
            self.fail("Packet must be UDP or TCP for INT tests")
        if INT_META_HDR not in pkt:
            self.fail("Packet must have INT_META_HDR")
        if INT_L45_HEAD not in pkt:
            self.fail("Packet must have INT_L45_HEAD")

        proto = UDP if UDP in pkt else TCP

        # will use runIPv4UnicastTest
        dst_mac = HOST2_MAC
        ig_port = self.port1
        eg_port = self.port2

        self.setup_transit(switch_id)

        instructions = self.get_ins_from_mask(pkt[INT_META_HDR].inst_mask)
        ins_cnt = len(instructions)
        assert ins_cnt == pkt[INT_META_HDR].ins_cnt

        # Forge expected packet based on pkt's ins_mask
        new_metadata, masked_ins_cnt = self.get_int_metadata(
            instructions=instructions, switch_id=switch_id,
            ig_port=ig_port, eg_port=eg_port)
        exp_pkt = pkt.copy()
        exp_pkt[INT_L45_HEAD].length += pkt[INT_META_HDR].ins_cnt
        exp_pkt[INT_META_HDR].total_hop_cnt += 1
        exp_pkt[INT_META_HDR].payload = new_metadata + str(exp_pkt[INT_META_HDR].payload)

        exp_pkt[Ether].src = exp_pkt[Ether].dst
        exp_pkt[Ether].dst = dst_mac
        if not mpls:
            exp_pkt[IP].ttl = exp_pkt[IP].ttl - 1
        else:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)

        if tagged2:
            # VLAN if tagged1 will be added by runIPv4UnicastTest
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_2)

        if ignore_csum or masked_ins_cnt > 0:
            mask_pkt = Mask(exp_pkt)
            if ignore_csum:
                csum_offset = len(exp_pkt) - len(exp_pkt[IP].payload) \
                              + (6 if proto is UDP else 16)
                mask_pkt.set_do_not_care(csum_offset * 8, 2 * 8)
            if masked_ins_cnt > 0:
                offset_metadata = len(exp_pkt) - len(exp_pkt[proto].payload) \
                                  + len(INT_L45_HEAD()) + len(INT_META_HDR()) \
                                  + (ins_cnt - masked_ins_cnt) * 4
                mask_pkt.set_do_not_care(offset_metadata * 8, masked_ins_cnt * 4 * 8)
            exp_pkt = mask_pkt

        self.runIPv4UnicastTest(pkt=pkt, next_hop_mac=HOST2_MAC,
                                tagged1=tagged1, tagged2=tagged2, mpls=mpls,
                                prefix_len=32, exp_pkt=exp_pkt)


class PppoeTest(DoubleVlanTerminationTest):

    def set_line_map(self, s_tag, c_tag, line_id):
        assert line_id != 0
        s_tag_ = stringify(s_tag, 2)  # outer
        c_tag_ = stringify(c_tag, 2)  # inner
        line_id_ = stringify(line_id, 4)

        # Upstream
        self.send_request_add_entry_to_action(
            "bng_ingress.t_line_map",
            [self.Exact("s_tag", s_tag_), self.Exact("c_tag", c_tag_)],
            "bng_ingress.set_line", [("line_id", line_id_)])

    def setup_line_v4(self, s_tag, c_tag, line_id, ipv4_addr, mac_src,
                      pppoe_session_id, enabled=True):
        assert s_tag != 0
        assert c_tag != 0
        assert line_id != 0
        assert pppoe_session_id != 0

        line_id_ = stringify(line_id, 4)
        mac_src_ = mac_to_binary(mac_src)
        ipv4_addr_ = ipv4_to_binary(ipv4_addr)
        pppoe_session_id_ = stringify(pppoe_session_id, 2)

        # line map common to up and downstream
        self.set_line_map(s_tag=s_tag, c_tag=c_tag, line_id=line_id)
        # Upstream
        if enabled:
            # Enable upstream termination.
            self.send_request_add_entry_to_action(
                "bng_ingress.upstream.t_pppoe_term_v4",
                [self.Exact("line_id", line_id_),
                 # self.Exact("eth_src", mac_src_),
                 self.Exact("ipv4_src", ipv4_addr_),
                 self.Exact("pppoe_session_id", pppoe_session_id_)],
                "bng_ingress.upstream.term_enabled_v4", [])

        # Downstream
        if enabled:
            a_name = "set_session"
            a_params = [
                ("pppoe_session_id", pppoe_session_id_),
            ]
        else:
            a_name = "drop"
            a_params = []
        self.send_request_add_entry_to_action(
            "bng_ingress.downstream.t_line_session_map",
            [self.Exact("line_id", line_id_)],
            "bng_ingress.downstream." + a_name, a_params)

    def set_upstream_pppoe_cp_table(self, pppoe_codes=()):
        for code in pppoe_codes:
            code_ = stringify(code, 1)
            self.send_request_add_entry_to_action(
                "bng_ingress.upstream.t_pppoe_cp",
                [self.Exact("pppoe_code", code_)],
                "bng_ingress.upstream.punt_to_cpu", [], DEFAULT_PRIORITY)

    def setup_bng(self, pppoe_cp_codes=PPPOED_CODES):
        self.set_upstream_pppoe_cp_table(pppoe_codes=pppoe_cp_codes)

    def read_pkt_count(self, c_name, line_id):
        counter = self.read_counter(c_name, line_id, typ="PACKETS")
        return counter.data.packet_count

    def read_byte_count(self, c_name, line_id):
        counter = self.read_counter(c_name, line_id, typ="BYTES")
        return counter.data.byte_count

    def read_pkt_count_upstream(self, type, line_id):
        return self.read_pkt_count("bng_ingress.upstream.c_" + type, line_id)

    def read_byte_count_upstream(self, type, line_id):
        return self.read_byte_count("bng_ingress.upstream.c_" + type, line_id)

    def read_byte_count_downstream_rx(self, line_id):
        return self.read_byte_count("bng_ingress.downstream.c_line_rx", line_id)

    def read_byte_count_downstream_tx(self, line_id):
        return self.read_byte_count("bng_egress.downstream.c_line_tx", line_id)

    def runUpstreamV4Test(self, pkt, tagged2, mpls, line_enabled=True):
        s_tag = vlan_id_outer = 888
        c_tag = vlan_id_inner = 777
        line_id = 99
        pppoe_session_id = 0xbeac
        core_router_mac = HOST1_MAC

        self.setup_bng()
        self.setup_line_v4(
            s_tag=s_tag, c_tag=c_tag, line_id=line_id, ipv4_addr=pkt[IP].src,
            mac_src=pkt[Ether].src, pppoe_session_id=pppoe_session_id, enabled=line_enabled)

        # Input is the given packet with double VLAN tags and PPPoE headers.
        pppoe_pkt = pkt_add_pppoe(pkt, type=1, code=PPPOE_CODE_SESSION_STAGE,
                                  session_id=pppoe_session_id)
        pppoe_pkt = pkt_add_vlan(pppoe_pkt, vlan_vid=vlan_id_inner)
        pppoe_pkt = pkt_add_vlan(pppoe_pkt, vlan_vid=vlan_id_outer)

        # Build expected packet from the input one, we expect it to be routed as
        # if it was without VLAN tags and PPPoE headers.
        exp_pkt = pkt.copy()
        exp_pkt = pkt_route(exp_pkt, core_router_mac)
        if tagged2:
            exp_pkt = pkt_add_vlan(exp_pkt, VLAN_ID_3)
        if mpls:
            exp_pkt = pkt_add_mpls(exp_pkt, MPLS_LABEL_2, DEFAULT_MPLS_TTL)
        else:
            exp_pkt = pkt_decrement_ttl(exp_pkt)

        # Read counters, will verify their values later.
        old_terminated = self.read_byte_count_upstream("terminated", line_id)
        old_dropped = self.read_byte_count_upstream("dropped", line_id)

        old_control = self.read_pkt_count_upstream("control", line_id)

        self.runPopAndRouteTest(
            pkt=pppoe_pkt, next_hop_mac=core_router_mac,
            exp_pkt=exp_pkt, out_tagged=tagged2,
            vlan_id=s_tag, inner_vlan_id=c_tag, verify_pkt=line_enabled,
            mpls=mpls)

        # Verify that upstream counters were updated as expected.
        if not self.is_bmv2():
            time.sleep(1)
        new_terminated = self.read_byte_count_upstream("terminated", line_id)
        new_dropped = self.read_byte_count_upstream("dropped", line_id)

        new_control = self.read_pkt_count_upstream("control", line_id)

        # No control plane packets here.
        self.assertEqual(new_control, old_control)

        # Using assertGreaterEqual because some targets may or may not count FCS
        if line_enabled:
            self.assertGreaterEqual(new_terminated, old_terminated + len(pppoe_pkt))
            self.assertEqual(new_dropped, old_dropped)
        else:
            self.assertEqual(new_terminated, old_terminated)
            self.assertGreaterEqual(new_dropped, old_dropped + len(pppoe_pkt))

    def runControlPacketInTest(self, pppoed_pkt, line_mapped=True):
        s_tag = vlan_id_outer = 888
        c_tag = vlan_id_inner = 777

        self.setup_bng()
        # If a line mapping is not provided, we expect packets to be processed
        # with line ID 0 (e.g. counters updated at index 0).
        line_id = 0
        if line_mapped:
            line_id = 99
            self.set_line_map(
                s_tag=s_tag, c_tag=c_tag, line_id=line_id)

        pppoed_pkt = pkt_add_vlan(pppoed_pkt, vlan_vid=vlan_id_outer)
        pppoed_pkt = pkt_add_inner_vlan(pppoed_pkt, vlan_vid=vlan_id_inner)

        old_terminated = self.read_byte_count_upstream("terminated", line_id)
        old_dropped = self.read_byte_count_upstream("dropped", line_id)
        old_control = self.read_pkt_count_upstream("control", line_id)

        testutils.send_packet(self, self.port1, str(pppoed_pkt))
        self.verify_packet_in(pppoed_pkt, self.port1)
        self.verify_no_other_packets()

        if not self.is_bmv2():
            time.sleep(1)
        new_terminated = self.read_byte_count_upstream("terminated", line_id)
        new_dropped = self.read_byte_count_upstream("dropped", line_id)

        new_control = self.read_pkt_count_upstream("control", line_id)

        # Only control plane packets.
        self.assertEqual(new_terminated, old_terminated)
        self.assertEqual(new_dropped, old_dropped)
        self.assertEqual(new_control, old_control + 1)

    def runControlPacketOutTest(self, pppoed_pkt):
        vlan_id_outer = 888
        vlan_id_inner = 777

        self.setup_bng()

        # Assuming pkts are double-tagged at the control plane.
        pppoed_pkt = pkt_add_vlan(pppoed_pkt, vlan_vid=vlan_id_inner)
        pppoed_pkt = pkt_add_vlan(pppoed_pkt, vlan_vid=vlan_id_outer)

        self.verify_packet_out(pppoed_pkt, self.port1)
        self.verify_no_other_packets()

    def runDownstreamV4Test(self, pkt, in_tagged, line_enabled):
        s_tag = vlan_id_outer = 888
        c_tag = vlan_id_inner = 777
        line_id = 99
        next_id = 99
        pppoe_session_id = 0xbeac
        olt_mac = HOST1_MAC

        self.setup_bng()
        self.setup_line_v4(
            s_tag=s_tag, c_tag=c_tag, line_id=line_id, ipv4_addr=pkt[IP].dst,
            mac_src=pkt[Ether].src, pppoe_session_id=pppoe_session_id, enabled=line_enabled)

        # Build expected packet from the input one, we expect it to be routed
        # and encapsulated in double VLAN tags and PPPoE.
        exp_pkt = pkt_add_pppoe(pkt, type=1, code=PPPOE_CODE_SESSION_STAGE, session_id=pppoe_session_id)
        exp_pkt = pkt_add_vlan(exp_pkt, vlan_vid=vlan_id_outer)
        exp_pkt = pkt_add_inner_vlan(exp_pkt, vlan_vid=vlan_id_inner)
        exp_pkt = pkt_route(exp_pkt, olt_mac)
        exp_pkt = pkt_decrement_ttl(exp_pkt)

        old_rx_count = self.read_byte_count_downstream_rx(line_id)
        old_tx_count = self.read_byte_count_downstream_tx(line_id)

        self.runRouteAndPushTest(
            pkt=pkt, next_hop_mac=olt_mac, exp_pkt=exp_pkt,
            in_tagged=in_tagged, next_id=next_id, next_vlan_id=s_tag, next_inner_vlan_id=c_tag,
            verify_pkt=line_enabled)

        if not self.is_bmv2():
            time.sleep(1)
        new_rx_count = self.read_byte_count_downstream_rx(line_id)
        new_tx_count = self.read_byte_count_downstream_tx(line_id)

        # Using assertGreaterEqual because some targets may or may not count FCS
        self.assertGreaterEqual(new_rx_count, old_rx_count + len(pkt))
        if line_enabled:
            self.assertGreaterEqual(new_tx_count, old_tx_count + len(pkt))
        else:
            self.assertEqual(new_tx_count, old_tx_count)
