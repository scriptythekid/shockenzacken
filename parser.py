#/usr/bin/env python


# ugly simple ioURT parser for shockenzacken/painoverTCP by scriptythekid 2012-2013
# mostly based on:
#	 ioUrT Parser for BigBrotherBot(B3) (www.bigbrotherbot.net)
#	 Copyright (C) 2008 Mark Weirath (xlr8or@xlr8or.com)
#

#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

#
#
#run: python parser.py .q3a/q3ut4/games.log
# with server running : ./ioUrTded.i386 +set fs_game q3ut4 +set dedicated 2 +set net_port 27960 +set com_hunkmegs 128 +exec server.cfg
# u have to set set g_loghits "1"  in server.cfg
# logfile should be in ~/.q3a/q3ut4/games.log
# u may want to configure sync'ed logging  ...
#

#FIXME throw this away and write a bigbrotherbot plugin... 

import re
import sys
import fileinput
import time

## kill modes
MOD_WATER='1'
MOD_LAVA='3'
MOD_TELEFRAG='5'
MOD_FALLING='6'
MOD_SUICIDE='7'
MOD_TRIGGER_HURT='9'
MOD_CHANGE_TEAM='10'
UT_MOD_KNIFE='12'
UT_MOD_KNIFE_THROWN='13'
UT_MOD_BERETTA='14'
UT_MOD_DEAGLE='15'
UT_MOD_SPAS='16'
UT_MOD_UMP45='17'
UT_MOD_MP5K='18'
UT_MOD_LR300='19'
UT_MOD_G36='20'
UT_MOD_PSG1='21'
UT_MOD_HK69='22'
UT_MOD_BLED='23'
UT_MOD_KICKED='24'
UT_MOD_HEGRENADE='25'
UT_MOD_SR8='28'
UT_MOD_AK103='30'
UT_MOD_SPLODED='31'
UT_MOD_SLAPPED='32'
UT_MOD_BOMBED='33'
UT_MOD_NUKED='34'
UT_MOD_NEGEV='35'
UT_MOD_HK69_HIT='37'
UT_MOD_M4='38'
UT_MOD_FLAG='39'
UT_MOD_GOOMBA='40'

## weapons id on Hit: lines are different than the one
## on the Kill: lines. Here the translation table
hitweapon2killweapon = {
  1: UT_MOD_KNIFE,
  2: UT_MOD_BERETTA,
  3: UT_MOD_DEAGLE,
  4: UT_MOD_SPAS,
  5: UT_MOD_MP5K,
  6: UT_MOD_UMP45,
  8: UT_MOD_LR300,
  9: UT_MOD_G36,
  10: UT_MOD_PSG1,
  14: UT_MOD_SR8,
  15: UT_MOD_AK103,
  17: UT_MOD_NEGEV,
  19: UT_MOD_M4,
  21: UT_MOD_HEGRENADE,
  22: UT_MOD_KNIFE_THROWN,
}

def _convertHitWeaponToKillWeapon( hitweapon_id):
  """on Hit: lines identifiers for weapons are different than
  the one on Kill: lines"""
  try:
    return hitweapon2killweapon[int(hitweapon_id)]
  except KeyError, err:
    print("unknown weapon id on Hit line: %s", err)
    return None

def _getDamagePoints(weapon, hitloc):
  try:
    points = damage[weapon][int(hitloc)]
    #print("_getDamagePoints(%s, %s) -> %s" % (weapon, hitloc, points))
    return points
  except KeyError, err:
    print("_getDamagePoints(%s, %s) cannot find value : %s" % (weapon, hitloc, err))
    return 15
    

""" From data provided by Garreth http://bit.ly/jf4QXc on http://bit.ly/krwBCv :

                                Head(0) Helmet(1)     Torso(2)     Kevlar(3)     Arms(4)    Legs(5)    Body(6)    Killed
    MOD_TELEFRAG='5'             0        0             0             0             0         0         0         0
    UT_MOD_KNIFE='12'           100      60            44            35            20        20        44        100
    UT_MOD_KNIFE_THROWN='13'    100      60            44            35            20        20        44        100
    UT_MOD_BERETTA='14'         100      34            30            20            11        11        30        100
    UT_MOD_DEAGLE='15'          100      66            57            38            22        22        57        100
    UT_MOD_SPAS='16'            25       25            25            25            25        25        25        100
    UT_MOD_UMP45='17'           100      51            44            29            17        17        44        100
    UT_MOD_MP5K='18'            50       34            30            20            11        11        30        100
    UT_MOD_LR300='19'           100      51            44            29            17        17        44        100
    UT_MOD_G36='20'             100      51            44            29            17        17        44        100
    UT_MOD_PSG1='21'            100      63            97            63            36        36        97        100
    UT_MOD_HK69='22'            50       50            50            50            50        50        50        100
    UT_MOD_BLED='23'            15       15            15            15            15        15        15        15
    UT_MOD_KICKED='24'          20       20            20            20            20        20        20        100
    UT_MOD_HEGRENADE='25'       50       50            50            50            50        50        50        100
    UT_MOD_SR8='28'             100      100           100           100           50        50        100       100
    UT_MOD_AK103='30'           100      58            51            34            19        19        51        100
    UT_MOD_NEGEV='35'           50       34            30            20            11        11        30        100
    UT_MOD_HK69_HIT='37'        20       20            20            20            20        20        20        100
    UT_MOD_M4='38'              100      51            44            29            17        17        44        100
    UT_MOD_GOOMBA='40'          100      100           100           100           100       100       100       100
    """
damage = {
  MOD_TELEFRAG: [0, 0, 0, 0, 0, 0, 0, 0],
  UT_MOD_KNIFE: [100, 60, 44, 35, 20, 20, 44, 100],
  UT_MOD_KNIFE_THROWN: [100, 60, 44, 35, 20, 20, 44, 100],
  UT_MOD_BERETTA: [100, 34, 30, 20, 11, 11, 30, 100],
  UT_MOD_DEAGLE: [100, 66, 57, 38, 22, 22, 57, 100],
  UT_MOD_SPAS: [25, 25, 25, 25, 25, 25, 25, 100],
  UT_MOD_UMP45: [100, 51, 44, 29, 17, 17, 44, 100],
  UT_MOD_MP5K: [50, 34, 30, 20, 11, 11, 30, 100],
  UT_MOD_LR300: [100, 51, 44, 29, 17, 17, 44, 100],
  UT_MOD_G36: [100, 51, 44, 29, 17, 17, 44, 100],
  UT_MOD_PSG1: [100, 63, 97, 63, 36, 36, 97, 100],
  UT_MOD_HK69: [50, 50, 50, 50, 50, 50, 50, 100],
  UT_MOD_BLED: [15, 15, 15, 15, 15, 15, 15, 15],
  UT_MOD_KICKED: [20, 20, 20, 20, 20, 20, 20, 100],
  UT_MOD_HEGRENADE: [50, 50, 50, 50, 50, 50, 50, 100],
  UT_MOD_SR8: [100, 100, 100, 100, 50, 50, 100, 100],
  UT_MOD_AK103: [100, 58, 51, 34, 19, 19, 51, 100],
  UT_MOD_NEGEV: [50, 34, 30, 20, 11, 11, 30, 100],
  UT_MOD_HK69_HIT: [20, 20, 20, 20, 20, 20, 20, 100],
  UT_MOD_M4: [100, 51, 44, 29, 17, 17, 44, 100],
  UT_MOD_GOOMBA: [100, 100, 100, 100, 100, 100, 100, 100],
}


hitrex = re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<acid>[0-9]+)\s(?P<hitloc>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>.*))$', re.IGNORECASE)

killrex = re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<acid>[0-9]+)\s(?P<cid>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>.*))$', re.IGNORECASE)

# remove the time off of the line
timerex = re.compile(r'^(?:[0-9:]+\s?)?')
    
linerexs= [hitrex, killrex]


testlines = '''
Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
Kill: 7 7 10: Mike_PL killed Mike_PL by MOD_CHANGE_TEAM
'''

fd = open(sys.argv[1], 'r')
print "opened ",sys.argv[1]
#sys.exit(1)
while True:
  for line in fd.readlines():
    line = line.strip() 		#remove leading/trailing whitespace so regexes match...!
    line = re.sub(timerex, '', line, 1)	#remove leading minutes/secs from logLine
    #print line
    
    for rex in linerexs:
      m = re.match(rex, line)
      if m:
	print line
	md = m.groupdict()
	if md['action'] == 'Hit':
	  wconv = _convertHitWeaponToKillWeapon(md['aweap'])
	  damageHP = None
	  try:
	    damageHP = _getDamagePoints(wconv, md['hitloc'])
	  except Exception, e:
	    #print "damagepoints error", md['hitloc']
	    pass
	  print md['acid'], md['action'], md['cid'], 'for ', damageHP, "damagepoints", "hitloc:", md['hitloc']
	  pass
	elif md['action'] == 'Kill':
	  print md['acid'], 'killed', md['cid'], 'with', md['aweap']
	
	break

    else:
      #print "no regex match for this line:"
      #print line
      pass
   
  #ugly way to reduce IO load? otherwise this script takes up 100% CPU ...
  time.sleep(0.01)
  
  
  
  
"""
damageHP = damage[aweap][hitloc]

# damage
    #Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
    #Hit: cid acid hitloc aweap: text

Hit: 9 8 8 8: =lvl4=Puma3_8 hit =lvl4=Puma4_9 in the Right Arm
Kill: 8 9 19: =lvl4=Puma3_8 killed =lvl4=Puma4_9 by UT_MOD_LR300

"""
"""
regexes
	#Generated with ioUrbanTerror v4.1:
        #Hit: 12 7 1 19: BSTHanzo[FR] hit ercan in the Helmet
        #Hit: 13 10 0 8: Grover hit jacobdk92 in the Head:
	re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<acid>[0-9]+)\s(?P<hitloc>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>.*))$', re.IGNORECASE),
        #re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<cid>[0-9]+)\s(?P<acid>[0-9]+)\s(?P<hitloc>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>(?P<aname>[^:])\shit\s(?P<name>[^:])\sin\sthe(?P<locname>.*)))$', re.IGNORECASE),

        #6:37 Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
        #2:56 Kill: 14 4 21: Qst killed Leftovercrack by UT_MOD_PSG1
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<acid>[0-9]+)\s(?P<cid>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>.*))$', re.IGNORECASE),
        #re.compile(r'^(?P<action>[a-z]+):\s(?P<data>(?P<acid>[0-9]+)\s(?P<cid>[0-9]+)\s(?P<aweap>[0-9]+):\s+(?P<text>(?P<aname>[^:])\skilled\s(?P<name>[^:])\sby\s(?P<modname>.*)))$', re.IGNORECASE),


 # kill
    #6:37 Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
    #6:37 Kill: 7 7 10: Mike_PL killed Mike_PL by MOD_CHANGE_TEAM
    #kill: acid cid aweap: <text>
    def OnKill(self, action, data, match=None):
        # kill modes caracteristics :
        
        1:      MOD_WATER === exclusive attackers : , 1022(<world>), 0(<non-client>)
        3:      MOD_LAVA === exclusive attackers : , 1022(<world>), 0(<non-client>)
        5:      MOD_TELEFRAG --- normal kill line
        6:      MOD_FALLING === exclusive attackers : , 1022(<world>), 0(<non-client>)
        7:      MOD_SUICIDE ===> attacker is always the victim
        9:      MOD_TRIGGER_HURT === exclusive attackers : , 1022(<world>)
        10:     MOD_CHANGE_TEAM ===> attacker is always the victim
        12:     UT_MOD_KNIFE --- normal kill line
        13:     UT_MOD_KNIFE_THROWN --- normal kill line
        14:     UT_MOD_BERETTA --- normal kill line
        15:     UT_MOD_DEAGLE --- normal kill line
        16:     UT_MOD_SPAS --- normal kill line
        17:     UT_MOD_UMP45 --- normal kill line
        18:     UT_MOD_MP5K --- normal kill line
        19:     UT_MOD_LR300 --- normal kill line
        20:     UT_MOD_G36 --- normal kill line
        21:     UT_MOD_PSG1 --- normal kill line
        22:     UT_MOD_HK69 --- normal kill line
        23:     UT_MOD_BLED --- normal kill line
        24:     UT_MOD_KICKED --- normal kill line
        25:     UT_MOD_HEGRENADE --- normal kill line
        28:     UT_MOD_SR8 --- normal kill line
        30:     UT_MOD_AK103 --- normal kill line
        31:     UT_MOD_SPLODED ===> attacker is always the victim
        32:     UT_MOD_SLAPPED ===> attacker is always the victim
        33:     UT_MOD_BOMBED --- normal kill line
        34:     UT_MOD_NUKED --- normal kill line
        35:     UT_MOD_NEGEV --- normal kill line
        37:     UT_MOD_HK69_HIT --- normal kill line
        38:     UT_MOD_M4 --- normal kill line
        39:     UT_MOD_FLAG === exclusive attackers : , 0(<non-client>)
        40:     UT_MOD_GOOMBA --- normal kill line
        self.debug('OnKill: %s (%s)'%(match.group('aweap'),match.group('text')))

"""



