import analysis_functions as analyze
from analysis_functions import *
import re
import json

def analyze_replay(link,cfg):
    rawlog = analyze.process(link)
    analyze.setlog(rawlog)

    pokelist = analyze.poke_list()
    p1_list = pokelist[1]
    p2_list = pokelist[2]

    format_type = analyze.gametype()

    if cfg['null_kd_all_doubles']:
        null_kd = True
    elif format_type == 'doubles' and cfg['prompt_null']:
        print('Doubles game detected: List un-shown pokemon with a "-/-" KD?')
        print('Y - yes\nN - no')
        while True:
            doubles_response = input('')
            if doubles_response.lower() == 'y':
                null_kd = True
                break
            elif doubles_response.lower() == 'n':
                null_kd = False
                break
            else:
                print('INVALID RESPONSE, please try again')
    else:
        null_kd = False

    player_names = analyze.pdata()

    p1_hazards = analyze.hazard_list('p1')
    p2_hazards = analyze.hazard_list('p2')

    analyze.set_hazardlists(p1_hazards[0],p1_hazards[1],p1_hazards[2],p2_hazards[0],p2_hazards[1],p2_hazards[2])

    cumulative_deaths = []
    cumulative_deaths_rectify = []
    dead_list = []
    for i in range(0,2):
        player_dead = analyze.dead(i)
        cumulative_deaths.extend(player_dead)
        dead_list.append(player_dead)

    for mon in cumulative_deaths:
        mon_rectified = re.sub(r'^p(\d)[abc]:',r'p\1.:',mon)
        if mon_rectified not in cumulative_deaths_rectify:
            cumulative_deaths_rectify.append(mon_rectified)

    cumulative_causes = []
    for mon in cumulative_deaths_rectify:
        cause_info = analyze.cause_of_death(mon)
        cumulative_causes.append((mon,cause_info))

    killer_list = []
    for ele in cumulative_causes:
        mon = ele[0]
        for death_info in ele[1]:
            flags = death_info[0]
            dead_turn = death_info[1]
            killer = kill_award(mon,flags,dead_turn)
            killer_list.append(killer)

    p1_kill_data = []
    p2_kill_data = []
    for mon in p1_list:
        kills = len(re.findall(mon[0],','.join(killer_list)))
        deaths = len(re.findall(mon[0],','.join(cumulative_deaths)))
        if re.findall(r'\|switch\|%s' % mon[0],analyze.log) == [] and null_kd:
            kills = '-'
            deaths = '-'
        p1_kill_data.append((mon[1],kills,deaths))

    for mon in p2_list:
        kills = len(re.findall(mon[0],','.join(killer_list)))
        deaths = len(re.findall(mon[0],','.join(cumulative_deaths)))
        if re.findall(r'\|switch\|%s' % mon[0],analyze.log) == [] and null_kd:
            kills = '-'
            deaths = '-'
        p2_kill_data.append((mon[1],kills,deaths))

    # preparing output payload
    printlines = []
    
    printlines.append('=-=-=-=-=-=-=-=-=-=\n')
    printlines.append(f'{player_names[0]} vs. {player_names[1]}\n')
    for p in p1_kill_data:
        printlines.append(f'{p[0]}\t{p[1]}\t{p[2]}\n')
    printlines.append('\n')
    for p in p2_kill_data:
        printlines.append(f'{p[0]}\t{p[1]}\t{p[2]}\n')
    printlines.append('=-=-=-=-=-=-=-=-=-=\n')
    
    # actually writing the lines to the file
    with open('output.txt','a') as out:
        for line in printlines:
            out.write(line)

# reading config from config.json
with open('config.json','r') as f:
    config = json.load(f)

# rudimentary UI
print('Welcome to the Mass Replay Analyzer')
print('Would you like to analyze 1 replay, or multiple replays from your clipboard?')
print('0 - Single Replay\n1 - Paste multiple')

while True:
    response = input('')

    if response == '0':
        clear = open('output.txt','w') # reset
        
        print('Please paste the replay link here: ',end='')
        replay = input('')
        replay = re.sub('\n|\?.+$','',replay)
        try:
            print(f'Now analyzing: {replay}')
            analyze_replay(replay,config)
        except:
            print('An error occured while analyzing')
        break
    elif response == '1':
        clear = open('output.txt','w') # reset
        
        replays = []
        print('Paste however many replays you\'d like.')
        print('Type "End" to stop pasting replays (not case sensitive)')
        while True:
            line = input('')
            if line.lower() == 'end':
                break
            replays.append(line)
        for replay in replays:
            replay = re.sub('\n|\?.+$','',replay)
            try:
                print(f'Now analyzing: {replay}')
                analyze_replay(replay,config)
            except:
                print('An error occured while analyzing')
        break
    else:
        print('INVALID RESPONSE, please try again')

print('PRESS ENTER TWICE TO CLOSE')
input('')
input('')
