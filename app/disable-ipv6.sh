#!/bin/sh

# Disable IPv6 at system level
echo "Disabling IPv6..."
echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6
echo 1 > /proc/sys/net/ipv6/conf/default/disable_ipv6

# Start nginx with IPv4 only
exec nginx -g "daemon off;"
