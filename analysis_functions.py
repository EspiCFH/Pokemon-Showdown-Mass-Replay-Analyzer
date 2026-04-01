import re
import requests

def process(l):
    link = re.sub(r'\s|\?p\d$|\n','',l) + '.log' # remove any unwanted additions to replay
    logfile = requests.get(link) #get log data
    return logfile.text

def setlog(l):
    global log, turnlist
    log = l
    turnlist = re.split(r'turn\|\d+',log)

def poke_list():
    p1_pokenames = []
    p2_pokenames = []
    
    p1_pokespec = re.findall(r'(?<=\|poke\|p1\|).*?(?=[,\|])',log) # get mon list in p1X: [name] format
    p2_pokespec = re.findall(r'(?<=\|poke\|p2\|).*?(?=[,\|])',log)
    
    for mon in p1_pokespec:
        try:
            name = re.findall(r'p1.:\s.+(?=\|%s)' % mon,log)[0]
            name = re.sub(r'^p1[abc]','p1.',name)
            p1_pokenames.append(name)
        except:
            p1_pokenames.append(f'p1.: {mon}')
        
    for mon in p2_pokespec:
        try:
           name = re.findall(r'p2.:\s.+(?=\|%s)' % mon,log)[0]
           name = re.sub(r'^p2[abc]','p2.',name)
           p2_pokenames.append(name)
        except:
            p2_pokenames.append(f'p2.: {mon}')
            
    p1_pokelist = list(zip(p1_pokenames,p1_pokespec))
    p2_pokelist = list(zip(p2_pokenames,p2_pokespec))

    pokelist = p1_pokelist + p2_pokelist
    
    return pokelist, p1_pokelist, p2_pokelist

def gametype():
    return re.findall(r'\|gametype\|(.+)(?=\n)',log)[-1]

def pdata():
    player_names = []
    unprocessed_names = re.findall(r'\|player\|p\d\|(.+\n)',turnlist[0])
    
    for n in unprocessed_names:
        processed_name = re.sub(r'\|.+\n$','',n) #remove avatar and elo
        if processed_name not in player_names: #remove any duplicates
            player_names.append(processed_name)

    return player_names

def hazard_list(player): #e.g. p1 means the hazards on p1's side
    rocks = []
    spikes = []
    tspikes = []
    opp = 'p2' if player == 'p1' else 'p1'
    # stealth rock
    rocker = ''
    for t in turnlist:
        if re.search(r'\|-sidestart\|%s.+\|move: Stealth Rock' % player, t):
            rocker = re.findall(r'\|move\|(%s.+)\|(?:Stealth Rock|Stone Axe)\|%s.+' % (opp,player),t)[0]
        elif re.search(r'\|-sideend\|%s.+\|Stealth Rock\|' % player,t):
            rocker = ''
        rocks.append(rocker)
    # spikes
    spike_users = []
    for t in turnlist:
        if re.search(r'\|-sideend\|%s.+\|Spikes\|' % player,t):
            spike_users.clear()
        if re.search(r'\|-sidestart\|%s.+\|Spikes' % player,t):
            spike = re.findall(r'\|move\|(%s.+)\|(?:Spikes|Ceaseless Edge)' % opp,t)
            spike_users.append(spike)
        spikes.append(spike_users)
    #toxic spikes
    tspike_users = []
    for t in turnlist:
        if re.search(r'\|-sideend\|%s.+\|move: Toxic Spikes\|' % player,t):
            tspike_users.clear()
        if re.search(r'\|-sidestart\|%s.+\|move: Toxic Spikes' % player,t):
            try:
                tspike = re.findall(r'\|move\|(%s.+)\|(?:Toxic Spikes)' % opp,t)
            except:
                tspike = re.findall(r'\|-activate\|(%s.+)\|ability: Toxic Debris' % opp,t)   
            tspike_users.extend(tspike)
        tspikes.append(tspike_users)
    return rocks, spikes, tspikes

def set_hazardlists(a,b,c,d,e,f): #easiest way to make it global here idk
    global p1_rocks, p1_spikes, p1_tspikes, p2_rocks, p2_spikes, p2_tspikes
    p1_rocks = a
    p1_spikes = b
    p1_tspikes = c
    p2_rocks = d
    p2_spikes = e
    p2_tspikes = f

def dead(player):
    return re.findall(r'\|faint\|(p%s\w:.+)(?=\n)' % (player + 1),log)

# next 3 functions are to reduce clutter in cause_of_death
def poison_flag(mon,cause,turn):
    psns = re.findall(r'\|-status\|%s\|(?:psn|tox)(?:\|\[from\].+)?' % mon,log)
    latest_psn = re.escape(psns[-1])

    for n,t in enumerate(turnlist[0:turn+1]):
        if re.search(latest_psn,t):
            poison_turn = n

    if re.search(r'\|-status\|%s\|tox\|\[from\] item: Toxic Orb' % mon,turnlist[poison_turn]):
        return 'orb'
    elif re.search(r'\|-activate\|.+\|ability: Synchronize\n%s' % latest_psn, turnlist[poison_turn]):
        return 'synchro'
    elif re.search(r'\[from\] ability:',latest_psn):
        return 'ability'
    elif re.search(r'\|switch\|%s\|[\s\S]+%s' % (mon,latest_psn),turnlist[poison_turn]) and len(re.findall(latest_psn,t))<2:
        return 'tspike'
    else:
        return None

def burn_flag(mon,cause,turn):
    brns = re.findall(r'\|-status\|%s\|(?:brn)(?:\|\[from\].+)?' % mon,log)
    latest_brn = re.escape(brns[-1])

    for n,t in enumerate(turnlist[0:turn+1]):
        if re.search(latest_brn,t):
            burn_turn = n

    if re.search(r'\|-status\|%s\|tox\|\[from\] item: Flame Orb' % mon,turnlist[burn_turn]):
        return 'orb'
    elif re.search(r'\|-activate\|.+\|ability: Synchronize\n%s' % latest_brn, turnlist[burn_turn]):
        return 'synchro'
    elif re.search(r'\[from\] ability:',latest_brn):
        return 'ability'
    # multiple lines of Beak Blast lmao
    beakpattern = r'\|-singleturn\|(.+)\|move: Beak Blast'
    if re.search(beakpattern,turnlist[burn_turn]):
        blasters = re.findall(beakpattern,turnlist[burn_turn])
        for b in blasters:
            if re.search(r'%s[\s\S]+\|move\|%s\|.+\|%s[\s\S]+\|-damage\|%s.+\n%s' % (beakpattern,mon,b,b,latest_brn),turnlist[burn_turn]):
                return 'beak'
    else:
        return None

def confusion_flag(mon,cause, turn):
    cnfs = re.findall(r'\|-start\|%s\|confusion' % mon,log)
    latest_cnf = re.escape(cnfs[-1])

    for n,t in enumerate(turnlist[0:turn+1]):
        if re.search(latest_cnf,t):
            cnf_turn = n

    if re.search(r'\|-heal\|%s\|.+\|\[from\] item: (Figy|Iapapa|Wiki|Aguav|Mago) Berry\n%s' % (mon,latest_cnf),turnlist[cnf_turn]):
        return None
    if re.search(r'\[fatigue\]',latest_cnf):
        return None
    if re.search(r'\|-boost\|%s\|atk\|2\|\[from\] item: Berserk Gene\n%s' % (mon,latest_cnf),turnlist[cnf_turn]):
        return None
    if re.search(r'\[from\] ability: ',latest_cnf):
        return 'ability'
    else:
        return 'reg'

def cause_of_death(mon):
    all_deaths = []
    
    volatile_DOT = ['Bind','Clamp','Fire Spin','Infestation',
               'Magma Storm','Sand Tomb','Snap Trap','Thunder Cage',
               'Whirlpool','Wrap','Salt Cure', 'Leech Seed', 'Nightmare',
               'Curse']
    
    for n,t in enumerate(turnlist):
        death_flags = ['direct',None]
        if re.search(r'\|-end\|%s\|move: (Future Sight|Doom Desire)[\s\S]*?\|-damage\|%s\|0 fnt' % (mon,mon), t):
            death_flags = ['misc','FS/DD']
        elif re.search(r'\|-start\|%s\|perish0\n' % mon,t):
            death_flags = ['misc','perish']
        elif re.search(r'\|-activate\|.+\|move: Destiny Bond\n\|faint\|%s' % mon,t):
            death_flags = ['misc','dbond']
        elif re.search(r'\|move\|%s\|(Healing Wish|Memento|Explosion).+\n\|(?!\|cant)' % mon,t):
            death_flags = ['self',None]
        elif re.search(r'\|-damage\|%s\|0 fnt\|\[from\]' % mon,t):
            deadfrom = re.findall(r'\|-damage\|%s\|0 fnt\|\[from\]\s(.+)' % mon,t)[-1]

            if deadfrom == 'item: Life Orb':
                death_flags = [None,None]

            elif deadfrom == 'psn':
                death_flags[0] = 'psn'
                death_flags[1] = poison_flag(mon,deadfrom,n)
            elif deadfrom == 'brn':
                death_flags[0] = 'brn'
                death_flags[1] = burn_flag(mon,deadfrom,n)
            elif deadfrom == 'confusion':
                death_flags[0] = 'confusion'
                death_flags[1] = confusion_flag(mon,deadfrom,n)

            elif deadfrom == 'Stealth Rock':
                death_flags[0] = 'rocks'
            elif deadfrom == 'Spikes':
                death_flags[0] = 'spikes'

            elif re.search(r'(move:\s)?(' + '|'.join(volatile_DOT)+')',deadfrom):
                death_flags[0] = 'DOT'
                if re.search(r'\[partiallytrapped\]',deadfrom):
                    death_flags[1] = 'trap'
                elif re.search(r'Leech Seed(\|\[|\n)',deadfrom):
                    death_flags[1] = 'leech'
                else:
                    death_flags[1] = 'switchable'

            elif re.search('ability',deadfrom):
                death_flags = ['misc','ability']
            elif re.search(r'item: Rocky Helmet',deadfrom):
                death_flags = ['misc','helmet']
            elif deadfrom == 'item: Sticky Barb':
                death_flags = ['misc','barb']
                
        if re.search(r'\|faint\|%s' % mon,t):
            all_deaths.append((death_flags,n))
            
    return all_deaths

def kill_award(mon,flags,turn):
    killer = None
    mon_player = mon[:2]
    opp_player = 'p2' if mon_player == 'p1' else 'p1'
    if flags[0] == 'direct':
        cropped_dead_turn = re.findall(r'^[\s\S]+\|faint\|%s' % mon,turnlist[turn])[0]
        # turn where the pokemon died but cropped at the point the pokemon in question dies
        # the purpose of this is to figure out which of a potential multiple attacks-
        # caused the kill on them
        move_candidates = re.findall(r'\|move\|(%s.+)\|.+\|%s.+\n' % (opp_player,mon_player),cropped_dead_turn)
        killer = move_candidates[-1] # implicitly this should always be the one

    elif flags[0] ==  'rocks':
        killer = globals()[f'{mon_player}_rocks'][turn]

    elif flags[0] == 'spikes':
        finalhp = int(re.findall(r'\|switch\|%s\|.+\|(\d+)\/100' % mon,turnlist[turn])[-1])
        if finalhp <= 13:
            spike_index = 0
        elif finalhp <= 18:
            spike_index = 1
        elif finalhp <= 25:
            spike_index = 2
        else:
            spike_index = 0  
        killer = globals()[f'{mon_player}_spikes'][turn][spike_index]
        
    elif flags[0] == 'psn':
        psns = re.findall(r'\|-status\|%s\|(?:psn|tox)(?:\|\[from\].+)?' % mon,log)
        latest_psn = re.escape(psns[-1])
        for n,t in enumerate(turnlist[0:turn+1]):
            if re.search(latest_psn,t):
                poison_turn = n
            
        if flags[1] == None:
            killer = re.findall(r'\|move\|(.+)\|.+\|%s[\s\S]+?\|-status\|%s\|(?:psn|tox)' % (mon,mon),turnlist[poison_turn])[-1]
            
        elif flags[1] == 'orb':
            # opponent tricks the mon an orb
            trick_pattern0 = r'\|-activate\|.+\|move: (?:Trick|Switcheroo)\|\[of\]%s\n\|-item\|%s\|(?:Toxic Orb)\|\[from\] move: (?:Trick|Switcheroo)' % (mon,mon)

            # the mon tricks and gets an orb
            trick_pattern1 = r'\|-activate\|%s\|move: (?:Trick|Switcheroo)\|\[of\] .+\n(?:.+\n)?.+\n\|-item\|%s\|(?:Toxic Orb)\|\[from\] move: (?:Trick|Switcheroo)' % (mon,mon)

            # this is actually for bestow
            trick_pattern2 = r'\|-item\|%s\|(?:Toxic Orb)\|\[from\] move: Bestow\|\[of\].+' % mon

            all_trick_patterns = [trick_pattern0,trick_pattern1,trick_pattern2]
            tricks = re.findall('|'.join(all_trick_patterns),'\n\n'.join(turnlist[1:poison_turn+1]))

            if len(tricks) > 0:
                trick_involved = re.findall(r'p\d[abc]: [^\|\n]+',tricks[-1])
                killer = [n for n in trick_involved if not re.search(mon,n)][0]
                
            elif re.search(r'\|-item\|%s\|Toxic Orb\|\[from\] ability: Magician\|' % mon,'\n\n'.join(turnlist[1:poison_turn+1])):
                killer = re.findall(r'\|-item\|%s\|Toxic Orb\|\[from\] ability: Magician\|\[of\] (.+)' % mon,'\n\n'.join(turnlist[1:poison_turn+1]))[-1]

        elif flags[1] == 'synchro':
            killer = re.findall(r'\|-activate\|(.+)\|ability: Synchronize\n\|-status\|%s\|(?:psn|tox)' % mon,turnlist[poison_turn])[-1]

        elif flags[1] == 'ability':
            killer = re.findall(r'\|-status\|%s\|(?:psn|tox)\|\[from\] ability: .+\|\[of\] (.+)',turnlist[poison_turn])[-1]
        elif flags[1] == 'tspike':
            mon_player = mon[:2]
            opp = 'p2' if mon_player == 'p1' else 'p1'
            
            finalhp = re.findall(r'%s\|(\d+)\/100' % mon,'\n\n'.join(turnlist[1:turn+1]))[-1]
            if int(finalhp) > 13:
                tspike_index = 1
            else:
                tspike_index = 0

            killer = globals()[f'{mon_player}_tspikes'][poison_turn][tspike_index]

    elif flags[0] == 'brn':
        brns = re.findall(r'\|-status\|%s\|(?:brn)(?:\|\[from\].+)?' % mon,log)
        latest_brn = re.escape(brns[-1])

        for n,t in enumerate(turnlist[0:turn+1]):
            if re.search(latest_brn,t):
                burn_turn = n
            
        if flags[1] == None:
            killer = re.findall(r'\|move\|(.+)\|.+\|%s[\s\S]+?\|-status\|%s\|brn' % (mon,mon),turnlist[burn_turn])[-1]
            
        elif flags[1] == 'orb':
            # opponent tricks the mon an orb
            trick_pattern0 = r'\|-activate\|.+\|move: (?:Trick|Switcheroo)\|\[of\]%s\n\|-item\|%s\|(?:Flame Orb)\|\[from\] move: (?:Trick|Switcheroo)' % (mon,mon)

            # the mon tricks and gets an orb
            trick_pattern1 = r'\|-activate\|%s\|move: (?:Trick|Switcheroo)\|\[of\] .+\n(?:.+\n)?.+\n\|-item\|%s\|(?:Flame Orb)\|\[from\] move: (?:Trick|Switcheroo)' % (mon,mon)

            # this is actually for bestow
            trick_pattern2 = r'\|-item\|%s\|(?:Flame Orb)\|\[from\] move: Bestow\|\[of\].+' % mon

            all_trick_patterns = [trick_pattern0,trick_pattern1,trick_pattern2]
            tricks = re.findall('|'.join(all_trick_patterns),'\n\n'.join(turnlist[1:burn_turn+1]))

            if len(tricks) > 0:
                trick_involved = re.findall(r'p\d[abc]: [^\|\n]+',tricks[-1])
                killer = [n for n in trick_involved if not re.search(mon,n)][0]
                
            elif re.search(r'\|-item\|%s\|Flame Orb\|\[from\] ability: Magician\|' % mon,'\n\n'.join(turnlist[1:burn_turn+1])):
                killer = re.findall(r'\|-item\|%s\|Flame Orb\|\[from\] ability: Magician\|\[of\] (.+)' % mon,'\n\n'.join(turnlist[1:burn_turn+1]))[-1]

        elif flags[1] == 'synchro':
            killer = re.findall(r'\|-activate\|(.+)\|ability: Synchronize\n\|-status\|%s\|brn' % mon,turnlist[burn_turn])[-1]

        elif flags[1] == 'ability':
            killer = re.findall(r'\|-status\|%s\|brn\|\[from\] ability: .+\|\[of\] (.+)',turnlist[burn_turn])[-1]
        elif flags[1] == 'beak':
            # beak blast redundancy from cause_of_death but makes things cleaner
            beakpattern = r'\|-singleturn\|(.+)\|move: Beak Blast'
            if re.search(beakpattern,turnlist[burn_turn]):
                blasters = re.findall(beakpattern,turnlist[burn_turn])
                for b in blasters:
                    if re.search(r'%s[\s\S]+\|move\|%s\|.+\|%s[\s\S]+\|-damage\|%s.+\n%s' % (beakpattern,mon,b,b,latest_brn),turnlist[burn_turn]):
                        killer = b

    elif flags[0] == 'confusion':
        cnfs = re.findall(r'\|-start\|%s\|confusion' % mon,log)
        latest_cnf = re.escape(cnfs[-1])

        for n,t in enumerate(turnlist[0:turn+1]):
            if re.search(latest_cnf,t):
                cnf_turn = n

        if flags[1] == 'reg':
            killer = re.findall(r'\|move\|(.+)\|.+\|%s\n(?:\|-boost\|%s.+\n)?(?:\|=damage\|.+\n)?\|-start\|%s\|confusion' % (mon,mon,mon),turnlist[cnf_turn])[-1]
        elif flags[1] == 'ability':
            killer = re.findall(r'\|-start\|%s\|confusion\|\[from\] ability:.+\|\[of\] (.+)' % mon,turnlist[cnf_turn])[-1]
        else:
            pass
    
    elif flags[0] == 'DOT':
        trapping = ['Bind','Clamp','Fire Spin','Infestation',
               'Magma Storm','Sand Tomb','Snap Trap','Thunder Cage',
               'Whirlpool','Wrap']
        switchable = ['Salt Cure','Nightmare', 'Curse']
        if flags[1] == 'trap':
            trap_pattern = r'\|-activate\|%s\|move: (?:' % mon + '|'.join(trapping) + r')\|\[of\] (.+)'
            killer = re.findall(trap_pattern,log)[-1]

        elif flags[1] == 'leech':
            killer = re.findall(r'\|-damage\|%s\|0 fnt\|\[from\] Leech Seed\|\[of\] (.+)' % mon,turnlist[turn])[0]

        elif flags[1] == 'switchable':
            killer = re.findall(r'\|move\|(.+)\|' + '|'.join(switchable) + r'%s\n(?:\|-.+)?\n\|-damage\|%s\|.+\n\|-start\|%s\|' % (mon,mon,mon),log)[-1]

    elif flags[0] == 'misc':
        if flags[1] == 'FS/DD':
            killer = re.findall(r'\|move\|(.+)\|(?:Future Sight|Doom Desire)\|%s.+\n\|-start\|' % mon[:3],turnlist[turn-2])[0]
        elif flags[1] == 'perish':
            perisher = re.findall(r'\|move\|(.+)\|Perish Song.+\n\|-start\|',turnlist[turn-3])[0]
            if perisher == mon:
                pass
            else:
                killer = perisher

        elif flags[1] == 'dbond':
            killer = re.findall(r'\|-activate\|(.+)\|move: Destiny Bond\n\|faint\|%s' % mon,turnlist[turn])[0]

        elif flags[1] == 'helmet':
            killer = re.findall(r'\|-damage\|%s\|0 fnt\|\[from\] item: Rocky Helmet\|\[of\] (.+)' % mon,turnlist[turn])[0]

        elif flags[1] == 'ability':
            killer = re.findall(r'\|-damage\|%s\|0 fnt\|\[from\] ability.+\|\[of\] (.+)' % mon,turnlist[turn])[0]

        elif flags[1] == 'barb':
            # opponent tricks the mon a barb
            trick_pattern0 = r'\|-activate\|.+\|move: (?:Trick|Switcheroo)\|\[of\]%s\n\|-item\|%s\|(?:Sticky Barb)\|\[from\] move: (?:Trick|Switcheroo)' % (mon,mon)

            # the mon tricks and gets a barb
            trick_pattern1 = r'\|-activate\|%s\|move: (?:Trick|Switcheroo)\|\[of\] .+\n(?:.+\n)?.+\n\|-item\|%s\|(?:Sticky Barb)\|\[from\] move: (?:Trick|Switcheroo)' % (mon,mon)

            # this is actually for bestow
            trick_pattern2 = r'\|-item\|%s\|(?:Sticky Barb)\|\[from\] move: Bestow\|\[of\].+' % mon

            all_trick_patterns = [trick_pattern0,trick_pattern1,trick_pattern2]
            #print('|'.join(all_trick_patterns))
        
            tricks = re.findall('|'.join(all_trick_patterns),'\n\n'.join(turnlist[1:turn+1]))
            if len(tricks) > 0:
                trick_involved = re.findall(r'p\d[abc]: [^\|\n]+',tricks[-1])
                killer = [n for n in trick_involved if not re.search(mon,n)][0]
                # I cannot presently account for takebacksies with a tricked barb bc it would-
                #require me to keep track of every possible switch and monitor the item changes-
                #of the other party too and do that for all the tricks and that's a lot of work-
                #for a niche scenario so forgive me (might change in the future who knows)
            else:
                # regrettably I cannot check for manual barb transfers because its very difficult-
                #to know for certain if there was a barb transfer since it doesnt explicitly tell you
                # it can be inductively reasoned but you cant tell if a pokemon starts with no item-
                #so its really hard
                pass
            
    return killer

