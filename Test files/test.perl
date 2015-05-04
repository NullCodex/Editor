#!/usr/bin/perl 
use strict;

use Net::SSH::Perl;

my $host = "10.168.100.130"
my $user = "admin"
my $password = "admin"

my $ssh = Net::SSH::Perl->new($host);

ssh->login($user, $pass);

my($stdout, $stderr, $exit) = $ssh->cmd("en ; admin; show policy");
print stdout;

