import requests
import re

#important variable for determing cause of death
volatileDOT = ['Bind','Clamp','Fire Spin','Infestation',
               'Magma Storm','Sand Tomb','Snap Trap','Thunder Cage',
               'Whirlpool','Wrap','Salt Cure']
def pokeList():
        global p1pL,p2pL
        #list of just the pokemon
        p1pL = []
        p2pL = []
        p1pLN = re.findall(r'(?<=\|poke\|p1\|).*?(?=[,\|])',rawlog)
        p2pLN = re.findall(r'(?<=\|poke\|p2\|).*?(?=[,\|])',rawlog)
        #identify the pokemon's nicknames and such
        for p in p1pLN:
            try:
                p1pL.append((re.findall(r'p1a:\s.+(?=\|%s)' % p,rawlog)[0],p))
            except:
                p1pL.append(('p1a: %s' % p,p))
        
        for p in p2pLN:
            try:
                p2pL.append((re.findall(r'p2a:\s.+(?=\|%s)' % p,rawlog)[0],p))
            except:
                p2pL.append(('p2a: %s' % p,p))

def kill_analyze():
    t_index = 0
    kill_list = []
    dead_list = []
    dead_to_rocks = []
    dead_to_spikes = []
    dead_to_other = []
    dead_to_psn = []
    for t in turnlist:
        turnspl = t.split('\n')
        for x in turnspl:
            if bool(re.search(r'-damage\|(.+)\|0 fnt',x)):
                dead = re.findall(r'(?<=\|)p.+(?=\|0 fnt)',x)[0]
                if bool(re.search(r'%s\|0 fnt\|\[from\]\s(Stealth Rock)' % dead,t)):
                   dead_to_rocks.append((dead,t_index))
                elif bool(re.search(r'%s\|0 fnt\|\[from\]\s(Spikes)' % dead,t)):
                   dead_to_spikes.append((dead,t_index))
                elif bool(re.search(r'%s\|0 fnt\|\[from\]\s(psn)' % dead,t)):
                    dead_to_psn.append((dead,t_index))
                elif bool(re.search(r'%s\|0 fnt\|\[from\]\s(brn|%s)' % (dead,'|.+|'.join(volatileDOT)),t)):
                    dead_to_other.append((dead,t_index))
                else:
                    killer = re.findall(r'(?<=\|move\|)p.+(?=\|.+\|%s)(?!\|\[notarget\])' % dead,t)[0]
                    kill_list.append(killer)
        fainted = re.findall(r'(?<=\|faint\|).+',t)
        dead_list.extend(fainted)
        t_index += 1
    return kill_list, dead_list, dead_to_rocks, dead_to_spikes, dead_to_other, dead_to_psn

def hazardTurns(player):
        #define the lists
        globals()[f'{player}SR'] = []
        globals()[f'{player}SP'] = []
        globals()[f'{player}TS'] = []
        if player == 'p1':
            opp = 'p2'
        elif player == 'p2':
            opp = 'p1'
        else:
            return None
        #stealth rock checks
        for t in turnlist:
            if bool(re.search(r'-sidestart\|%s:.+Stealth Rock' % player,t)):
                rocker = re.findall(r'(?<=\|move\|)%sa:.+?(?=\|)' % opp,t)[0]
                globals()[f'{player}SR'].append(rocker)
            elif bool(re.search(r'-sideend\|%s.+Stealth Rock' % player,t)):
                globals()[f'{player}SR'].append(rocker)
                rocker = ''
            else:
                try:
                   globals()[f'{player}SR'].append(rocker)
                except:
                    globals()[f'{player}SR'].append('')
        #spikes checks
        spikers = []
        for t in turnlist:
            if bool(re.search(r'-sideend\|%s:.+\|Spikes' % player,t)):
                spikers.clear()
            if bool(re.search(r'-sidestart\|%s:.+\|Spikes' % player,t)):
                spike = re.findall(r'(?<=\|move\|)%sa:.+?(?=\|)' % opp,t)[0]
                spikers.append(spike)
            globals()[f'{player}SP'].append(list(spikers))
        #toxic spikes checks
        tspikers = []
        for t in turnlist:
            if bool(re.search(r'-sideend\|%s:.+\|Toxic Spikes' % player,t)):
                tspikers.clear()
            if bool(re.search(r'-sidestart\|%s:.+\|move: Toxic Spikes' % player,t)):
                try:
                    tspike = re.findall(r'(?<=\|move\|)%sa:.+?(?=\|)' % opp,t)[0]
                except:
                    try:
                        tspike = re.findall(r'(?<=\|-activate\|)p2a:.+?(?=\|.+Toxic Debris)' % opp,t)[0]
                    except:
                        pass
                tspikers.append(tspike)
            globals()[f'{player}TS'].append(list(tspikers))
        return globals()[f'{player}SR'], globals()[f'{player}SP'], globals()[f'{player}TS']

#second analysis, for awarding indirect kills
def indirectAward(mode):
    if mode == 'hazards':
        for mon in dead_to_rocks:
            monplayer = mon[0][:2]
            hazardkiller = globals()[f'{monplayer}SR'][mon[1]]
            #print(hazardkiller)
            try:
                kill_list.append(hazardkiller)
            except:
                pass
        for mon in dead_to_spikes:
            monplayer = mon[0][:2]
            prespikeHealth = re.findall(r'\d*(?=\/100\n\|-damage\|%s\|0 fnt\|\[from\]\sSpikes)' % mon[0],rawlog)[0]
            if int(prespikeHealth) < 13:
                spiker_index = 0
            elif int(prespikeHealth) < 18:
                spiker_index = 1
            else:
                spiker_index = 2
            hazardkiller = globals()[f'{monplayer}SP'][mon[1]][spiker_index]
            #print(hazardkiller)
            try:
                kill_list.append(hazardkiller)
            except:
                pass
    elif mode == 'psn':
        for mon in dead_to_psn:
            monplayer = mon[0][:2]
            psns = re.findall(r'\|-status\|%s\|(?:psn|tox)(?:\|\[from\].+)?\n' % mon[0],rawlog)
            latestpsn = re.escape(psns[-1])
            #toxic orb check
            if bool(re.search('Toxic Orb',psns[-1])):
                if bool(re.search(r'\|-item\|%s\|Toxic Orb\|\[from\] move: (?:Trick|Switcheroo)' % mon[0], re.findall(r'[\s\S]+%s' % latestpsn,rawlog)[0])):
                    #poisoner candidates
                    psnr_c = re.findall(r'\|-activate\|(.+|%s)\|move: Trick\|\[of\] (%s|.+)' % (mon[0],mon[0]),re.findall(r'[\s\S]+%s' % latestpsn,rawlog)[0])[-1]
                    psnr = [x for x in psnr_c if x != mon[0]][0]
                else:
                    psnr = re.findall(r'\|-item\|%s\|Toxic Orb\|\[from\].+Magician\|\[of\]\s(.+)' % mon[0],re.findall(r'[\s\S]+%s' % latestpsn,rawlog)[0])[-1]
            else:
                for t in reversed(turnlist):
                    if bool(re.search(r'\|switch\|%s\|.+\n%s' % (mon[0],latestpsn),t)) and len(re.findall(latestpsn,t)) == 1:
                        finalhp = re.findall(r'\|%s\|.*?(\d*)\/100' % mon[0],turnlist[mon[1]])[-1]
                        if int(finalhp) <= 13:
                            tspike_index = 0
                        else:
                            tspike_index = -1
                        psnr = globals()[r'%sTS' % monplayer][mon[1]][tspike_index]
                        #this determined which tspiker gets the kill
                    elif bool(re.search(latestpsn,t)):
                        #poisoner_candidates
                        psnr_c = re.findall(r'\|(p[^%s]a: .+)\|' % monplayer,t)
                        psnr = [x for x in psnr_c if '|' not in x][0]
            try:
                kill_list.append(psnr)
            except:
                pass
    elif mode == 'other':
        #other includes burn, tricked barbs, salt cure, trapping effects
        for mon in dead_to_other:
            monplayer = mon[0][:2]
            #check for burn
            if bool(re.search(r'\|-damage\|%s\|0 fnt\|\[from\] brn' % mon[0],rawlog)):
                burns = re.findall(r'\|-status\|%s\|brn(?:\|\[from\].+)?\n' % mon[0],rawlog)
                latestburn = re.escape(burns[-1])
                #print(burns,latestburn,sep='\n')
                #flame orb check
                if bool(re.search('Flame Orb',burns[-1])):
                    if bool(re.search(r'\|-item\|%s\|Flame Orb\|\[from\] move: (?:Trick|Switcheroo)' % mon[0], re.findall(r'[\s\S]+%s' % latestburn,rawlog)[0])):
                        #burner candidates
                        burner_c = re.findall(r'\|-activate\|(.+|%s)\|move: Trick\|\[of\] (%s|.+)' % (mon[0],mon[0]),re.findall(r'[\s\S]+%s' % latestburn,rawlog)[0])[-1]
                        burner = [x for x in burner_c if x != mon[0]][0]
                        #print(burner)
                    else:
                        burner = re.findall(r'\|-item\|%s\|Flame Orb\|\[from\].+Magician\|\[of\]\s(.+)' % mon[0],re.findall(r'[\s\S]+%s' % latestburn,rawlog)[0])[-1]
                        #print(burner)
                else:
                    for t in reversed(turnlist):
                        if bool(re.search(latestburn,t)):
                            #burner_candidates
                            burner_c = re.findall(r'\|(p[^%s]a: .+)\|' % monplayer,t)
                            burner = [x for x in burner_c if '|' not in x][0]
                            #print(burner)
                kill_list.append(burner)
            #volatile damage-over-time check
            elif bool(re.search(r'(?<=\n\|-damage\|%s\|0 fnt\|\[from\]\s).+(?!brn|.+Sticky Barb)' % mon[0],turnlist[mon[1]])):
                widenet = re.findall(r'(?<=\n\|-damage\|%s\|0 fnt\|\[from\]).+' % mon[0],turnlist[mon[1]])[0]
                try:
                   smallnet = re.sub(r'\s*?move:\s|\|\[partiallytrapped\]','',widenet)
                except:
                    smallnet = widenet
                if smallnet in volatileDOT:
                    for t in turnlist:
                        #check if a pokemon clicked the killing move on the dead
                        if bool(re.search(r'\|move\|.+\|%s\|%s\n' % (smallnet, mon[0]),t)):
                            switchflag = False
                            lastuser = re.findall(r'(?<=\|move\|).+(?=\|%s\|%s\n)' % (smallnet, mon[0]),t)[0]
                        #check if the pokemon switched out of the volatile effect
                        elif bool(re.search(r'\switch\|%s' % mon[0],t)):
                            switchflag = True
                        else:
                            pass
                    #gives the kill to the last user of the volatile move
                    if switchflag == False:
                        killer = lastuser
                        #print(killer)
                        kill_list.append(killer)
            #check for sticky barb
            if bool(re.search(r'(?<=\n\|-damage\|%s\|0 fnt\|\[from\]\s).+Sticky Barb' % mon[0],turnlist[mon[1]])):
                if bool(re.search(r'\|-item\|%s\|Sticky Barb\|\[from\] move: (?:Trick|Switcheroo)' % mon[0],rawlog)):
                    barber_c = re.findall(r'\|-activate\|(.+|%s)\|move: Trick\|\[of\] (%s|.+)' % (mon[0],mon[0]),rawlog)[-1]
                    barber = [x for x in barber_c if x != mon[0]][0]
                    kill_list.append(barber)
                else:
                    try:
                        barber = re.findall(r'\|-item\|%s\|Sticky Barb\|\[from\].+Magician\|\[of\]\s(.+)' % mon[0],rawlog)[-1]
                        kill_list.append(barber)
                    except:
                        pass
            else:
                pass

def analyzeReplay(r):
    global kill_list, dead_list, dead_to_rocks, dead_to_spikes, dead_to_other, dead_to_psn, rawlog, turnlist, loglines
    link = r + '.log'
    #get replay log
    logfile = requests.get(link)
    rawlog = logfile.text
    #text cleaning
    loglines = rawlog.split('\n')
    turnlist = re.split(r'turn\|\d+',rawlog)
    turnlist.pop(0)
    
    pokeList()
    p1hazards = hazardTurns('p1')
    p2hazards = hazardTurns('p2')
    kill_sources = kill_analyze()
    #define variables from first analysis
    kill_list = kill_sources[0]
    dead_list = kill_sources[1]
    dead_to_rocks = kill_sources[2]
    dead_to_spikes = kill_sources[3]
    dead_to_other = kill_sources[4]
    dead_to_psn = kill_sources[5]
    #important variables for second analysis
    switchflag = True
    lastuser = ''

    indirectAward('hazards')
    indirectAward('psn')
    indirectAward('other')

    #kill counting
    player1name = re.findall(r'\|player\|p1\|(.+)\|.+\n',rawlog)[0]
    player2name = re.findall(r'\|player\|p2\|(.+)\|.+\n',rawlog)[0]
    printlines = []
    printlines.append('=-=-=-=-=-=-=-=-=-=\n')
    printlines.append(f'{player1name} vs. {player2name}\n')
    #p1 kill tally
    for p in p1pL:
        kills = sum(1 if p[0] == x else 0 for x in kill_list)
        deaths = sum(1 if p[0] == x else 0 for x in dead_list)
        printlines.append(f'{p[1]}\t{kills}\t{deaths}\n')
    printlines.append('\n')
    #p2 kill tally
    for p in p2pL:
        kills = sum(1 if p[0] == x else 0 for x in kill_list)
        deaths = sum(1 if p[0] == x else 0 for x in dead_list)
        printlines.append(f'{p[1]}\t{kills}\t{deaths}\n')
    printlines.append('=-=-=-=-=-=-=-=-=-=\n')
    with open('output.txt','a') as output:
        for line in printlines:
            output.write(line)


print('Welcome to the Mass Replay Analyzer')
print('Would you like to analyze 1 replay or multiple replays from a list?')
print('(Replays can be pasted line by line in replay.txt in the same directory')
print('0 - Single Replay\n1 - Multiple')
while True:
    response = input('')
    if response == '0':
        print('Please paste the replay link here:')
        clear = open('output.txt','w')
        replay = input('')
        analyzeReplay(replay)
        break
    elif response == '1':
        clear = open('output.txt','w')
        rfile = open('replays.txt')
        rlist = rfile.readlines()
        for r in rlist:
            analyzeReplay(r.replace('\n',''))
        break
    else:
        print('INVALID RESPONSE, please try again')

print('PRESS ENTER TWICE TO CLOSE')
input('')
input('')
