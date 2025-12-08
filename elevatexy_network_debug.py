#!/usr/bin/env python3
"""
ElevateXY Network Debugging Tool
Tests UDP connectivity between ArduCopter simulation and Jetson
"""

import socket
import sys
import time
import subprocess
import struct
from threading import Thread

class NetworkDebugger:
    def __init__(self):
        self.test_results = {}
        
    def print_header(self, title):
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def test_network_interfaces(self):
        """Test available network interfaces"""
        self.print_header("1. Network Interfaces")
        
        try:
            # Get all network interfaces
            result = subprocess.run(['ip', 'addr', 'show'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            
            # Get routing table
            print("\nRouting Table:")
            result = subprocess.run(['ip', 'route'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            
            self.test_results['interfaces'] = True
        except Exception as e:
            print(f"❌ Error checking interfaces: {e}")
            self.test_results['interfaces'] = False
    
    def test_hostname_resolution(self):
        """Test hostname resolution"""
        self.print_header("2. Hostname Resolution")
        
        try:
            hostname = socket.gethostname()
            print(f"Hostname: {hostname}")
            
            ip = socket.gethostbyname(hostname)
            print(f"IP Address: {ip}")
            
            # Get all IPs
            print("\nAll IP addresses:")
            result = subprocess.run(['hostname', '-I'], 
                                  capture_output=True, text=True)
            print(result.stdout)
            
            self.test_results['hostname'] = True
        except Exception as e:
            print(f"❌ Error with hostname: {e}")
            self.test_results['hostname'] = False
    
    def test_udp_port_available(self, port):
        """Test if UDP port is available"""
        self.print_header(f"3. UDP Port {port} Availability")
        
        try:
            # Try to bind to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', port))
            sock.close()
            
            print(f"✅ Port {port} is available")
            self.test_results[f'port_{port}_available'] = True
        except Exception as e:
            print(f"❌ Port {port} unavailable: {e}")
            self.test_results[f'port_{port}_available'] = False
    
    def test_udp_listener(self, port, duration=10):
        """Create UDP listener to test incoming packets"""
        self.print_header(f"4. UDP Listener on Port {port}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.bind(('0.0.0.0', port))
            
            print(f"Listening on 0.0.0.0:{port}")
            print(f"Waiting {duration} seconds for packets...")
            print("(Start your ArduCopter simulation now if not running)")
            
            start_time = time.time()
            packet_count = 0
            
            while (time.time() - start_time) < duration:
                try:
                    data, addr = sock.recvfrom(4096)
                    packet_count += 1
                    print(f"\n✅ Received packet #{packet_count}")
                    print(f"   From: {addr}")
                    print(f"   Size: {len(data)} bytes")
                    print(f"   First 50 bytes: {data[:50]}")
                    
                    # Try to identify MAVLink packets
                    if len(data) > 0:
                        if data[0] == 0xFD:  # MAVLink 2.0
                            print(f"   Type: MAVLink 2.0 packet")
                        elif data[0] == 0xFE:  # MAVLink 1.0
                            print(f"   Type: MAVLink 1.0 packet")
                        else:
                            print(f"   Type: Unknown (first byte: 0x{data[0]:02x})")
                    
                except socket.timeout:
                    sys.stdout.write('.')
                    sys.stdout.flush()
            
            sock.close()
            
            print(f"\n\nTotal packets received: {packet_count}")
            
            if packet_count > 0:
                print("✅ UDP reception working!")
                self.test_results['udp_receive'] = True
            else:
                print("❌ No packets received")
                self.test_results['udp_receive'] = False
                
        except Exception as e:
            print(f"❌ Error in UDP listener: {e}")
            self.test_results['udp_receive'] = False
    
    def test_udp_sender(self, target_ip, target_port, source_port=14551):
        """Test sending UDP packets"""
        self.print_header(f"5. UDP Sender to {target_ip}:{target_port}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', source_port))
            
            # Send test packet
            test_message = b"ElevateXY_TEST_PACKET"
            sock.sendto(test_message, (target_ip, target_port))
            
            print(f"✅ Sent test packet to {target_ip}:{target_port}")
            print(f"   From port: {source_port}")
            print(f"   Message: {test_message}")
            
            sock.close()
            self.test_results['udp_send'] = True
            
        except Exception as e:
            print(f"❌ Error sending UDP: {e}")
            self.test_results['udp_send'] = False
    
    def test_firewall(self, port):
        """Check firewall status"""
        self.print_header(f"6. Firewall Status for Port {port}")
        
        try:
            # Check if ufw is installed and active
            result = subprocess.run(['which', 'ufw'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                result = subprocess.run(['sudo', 'ufw', 'status'], 
                                      capture_output=True, text=True)
                print(result.stdout)
                
                if 'inactive' in result.stdout.lower():
                    print("✅ Firewall is inactive")
                    self.test_results['firewall'] = True
                else:
                    print("⚠️ Firewall is active - may block UDP")
                    print(f"\nTo allow port {port}:")
                    print(f"  sudo ufw allow {port}/udp")
                    self.test_results['firewall'] = False
            else:
                print("No ufw firewall detected")
                self.test_results['firewall'] = True
                
        except Exception as e:
            print(f"❌ Error checking firewall: {e}")
            self.test_results['firewall'] = None
    
    def test_ping(self, target_ip):
        """Test ping connectivity"""
        self.print_header(f"7. Ping Test to {target_ip}")
        
        try:
            result = subprocess.run(['ping', '-c', '4', target_ip], 
                                  capture_output=True, text=True, timeout=10)
            print(result.stdout)
            
            if result.returncode == 0:
                print(f"✅ Can ping {target_ip}")
                self.test_results['ping'] = True
            else:
                print(f"❌ Cannot ping {target_ip}")
                self.test_results['ping'] = False
                
        except Exception as e:
            print(f"❌ Ping error: {e}")
            self.test_results['ping'] = False
    
    def test_mavproxy_connection(self, connection_string):
        """Test DroneKit connection"""
        self.print_header("8. DroneKit Connection Test")
        
        print(f"Testing connection to: {connection_string}")
        print("This may take up to 60 seconds...")
        
        try:
            from dronekit import connect
            
            print("Attempting connection...")
            vehicle = connect(connection_string, wait_ready=False, timeout=30)
            
            print("✅ Connected!")
            print(f"   Mode: {vehicle.mode.name}")
            print(f"   Armed: {vehicle.armed}")
            print(f"   System status: {vehicle.system_status.state}")
            
            vehicle.close()
            self.test_results['dronekit'] = True
            
        except Exception as e:
            print(f"❌ DroneKit connection failed: {e}")
            self.test_results['dronekit'] = False
            print("\nCommon issues:")
            print("1. ArduCopter simulation not running")
            print("2. Wrong connection string format")
            print("3. Network/radio connectivity issue")
            print("4. Incorrect baud rate")
    
    def run_comprehensive_test(self, 
                              listen_port=14550, 
                              target_ip="127.0.0.1",
                              target_port=14551,
                              connection_string="udp:127.0.0.1:14550"):
        """Run all tests"""
        print("\n" + "="*70)
        print("  ELEVATEXY NETWORK DEBUGGING TOOL")
        print("="*70)
        
        # Basic network tests
        self.test_network_interfaces()
        self.test_hostname_resolution()
        
        # Port tests
        self.test_udp_port_available(listen_port)
        self.test_firewall(listen_port)
        
        # Connectivity tests
        self.test_ping(target_ip)
        self.test_udp_sender(target_ip, target_port, listen_port)
        
        # Packet reception test
        print("\n⚠️  IMPORTANT: Make sure ArduCopter simulation is running!")
        print("   For SITL: sim_vehicle.py -v ArduCopter -L LOCATION --out=udp:JETSON_IP:14550")
        input("\nPress Enter when ArduCopter is ready...")
        
        self.test_udp_listener(listen_port, duration=10)
        
        # DroneKit test
        self.test_mavproxy_connection(connection_string)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        passed = sum(1 for v in self.test_results.values() if v is True)
        failed = sum(1 for v in self.test_results.values() if v is False)
        
        print(f"\n✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        print("\nDetailed Results:")
        for test, result in self.test_results.items():
            if result is True:
                status = "✅ PASS"
            elif result is False:
                status = "❌ FAIL"
            else:
                status = "⚠️  UNKNOWN"
            print(f"  {status}  {test}")
        
        # Recommendations
        print("\n" + "="*70)
        print("  RECOMMENDATIONS")
        print("="*70)
        
        if not self.test_results.get('udp_receive', False):
            print("\n❌ No UDP packets received. Check:")
            print("   1. ArduCopter simulation is running")
            print("   2. ArduCopter output is configured: --out=udp:JETSON_IP:14550")
            print("   3. Network route between devices")
            print("   4. Firewall rules")
        
        if not self.test_results.get('dronekit', False):
            print("\n❌ DroneKit connection failed. Try:")
            print("   1. Verify UDP packets are being received first")
            print("   2. Check connection string format")
            print("   3. Use udpin: instead of udp: for listening mode")
            print("      Example: 'udpin:0.0.0.0:14550'")
        
        if self.test_results.get('udp_receive', False) and not self.test_results.get('dronekit', False):
            print("\n⚠️  UDP works but DroneKit fails:")
            print("   This suggests a protocol/parsing issue, not network")
            print("   Try connection string: 'udpin:0.0.0.0:14550'")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ElevateXY Network Debugging')
    parser.add_argument('--listen-port', type=int, default=14550,
                       help='UDP port to listen on (default: 14550)')
    parser.add_argument('--target-ip', default='127.0.0.1',
                       help='Target IP for testing (default: 127.0.0.1)')
    parser.add_argument('--target-port', type=int, default=14551,
                       help='Target UDP port (default: 14551)')
    parser.add_argument('--connection', default='udpin:0.0.0.0:14550',
                       help='DroneKit connection string')
    parser.add_argument('--quick', action='store_true',
                       help='Skip packet listening test')
    
    args = parser.parse_args()
    
    debugger = NetworkDebugger()
    
    if args.quick:
        # Quick tests only
        debugger.test_network_interfaces()
        debugger.test_hostname_resolution()
        debugger.test_udp_port_available(args.listen_port)
        debugger.test_ping(args.target_ip)
        debugger.print_summary()
    else:
        # Full comprehensive test
        debugger.run_comprehensive_test(
            listen_port=args.listen_port,
            target_ip=args.target_ip,
            target_port=args.target_port,
            connection_string=args.connection
        )

if __name__ == "__main__":
    main()
