# -*- coding: UTF-8 -*-

import psyco
psyco.full()

import ctypes

import es
import est
import spe
import random
import esc
import cmdlib
import playerlib
import msglib
import gamethread
import repeat
import usermsg
import popuplib
import spe_effects

sv = es.ServerVar
_healthprop = "CBasePlayer.m_iHealth"
_moneyprop = "CCSPlayer.m_iAccount"
_armorprop = "CCSPlayer.m_ArmorValue"
_helmetprop = "CCSPlayer.m_bHasHelmet"
_punchangle = "CBasePlayer.localdata.m_Local.m_vecPunchAngle"
_teamprop = "CBaseEntity.m_iTeamNum"
_blockprop = "CBaseEntity.m_CollisionGroup"
_movetype = "CBaseEntity.movetype"
_deadflag = "CBasePlayer.pl.deadflag"
_waterlevel = "CBasePlayer.localdata.m_nWaterLevel"
_speedprop = "CBasePlayer.localdata.m_flLaggedMovementValue"
allweapons = ("weapon_ak47", "weapon_aug", "weapon_awp", "weapon_c4", "weapon_deagle", "weapon_elite", "weapon_famas", "weapon_fiveseven", "weapon_flashbang", "weapon_g3sg1", "weapon_galil", "weapon_glock", "weapon_hegrenade", "weapon_knife", "weapon_m249", "weapon_m3", "weapon_m4a1", "weapon_mac10", "weapon_mp5navy", "weapon_p228", "weapon_p90", "weapon_scout", "weapon_sg550", "weapon_sg552", "weapon_smokegrenade", "weapon_tmp", "weapon_ump45", "weapon_usp", "weapon_xm1014")

NPC_MAPS = ["cs_office"]
TR_MAPS = ["cs_office", "de_biolab_v2"]
STORY_PHONEECHO = [0]
ONLINE_MAPS = []
ONLINE = True
IN_ATTACK = (1 << 0)
IN_JUMP = (1 << 1)
IN_DUCK = (1 << 2)
IN_FORWARD = (1 << 3)
IN_BACK = (1 << 4)
IN_USE = (1 << 5)
IN_CANCEL = (1 << 6)
IN_LEFT = (1 << 7)
IN_RIGHT = (1 << 8)
IN_MOVELEFT = (1 << 9)
IN_MOVERIGHT = (1 << 10)
IN_ATTACK2 = (1 << 11)
IN_RUN = (1 << 12)
IN_RELOAD = (1 << 13)
IN_ALT1 = (1 << 14)
IN_ALT2 = (1 << 15)
IN_SCORE = (1 << 16)   # Used by client.dll for when scoreboard is held down
IN_SPEED = (1 << 17) # Player is holding the speed key
IN_WALK = (1 << 18) # Player holding walk key
IN_ZOOM = (1 << 19)# Zoom key for HUD zoom
IN_WEAPON1 = (1 << 20) # weapon defines these bits
IN_WEAPON2 = (1 << 21) # weapon defines these bits
IN_BULLRUSH = (1 << 22)
IN_GRENADE1 = (1 << 23) # grenade 1
IN_GRENADE2 = (1 << 24) # grenade 2
IN_ATTACK3 = (1 << 25)

def load():
    es.set("eventscripts_noisy", 1)
    spe.parseINI("the_killers/sig.ini")
    spe.parseTypesINI("the_killers/twosig.ini")
    spe.registerPreHook('player_hurt', pre_player_hurt)
    spe.registerPreHook('weapon_fire', pre_weapon_fire)
    cmdlib.registerServerCommand('r_weaponswap', weapon_swap, "None")
    spe.detourFunction("PlayerRunCommand", spe.HookType.Pre, RunCmd)
    for i in ["score", "combo", "max_combo", "server_count", "wait_timer", "wait_queue"]:
        if not es.exists('variable', i):
            es.set(i, 0)
    global first_join
    first_join = []
    global shot_queue
    shot_queue = {}
    global active_weapon
    active_weapon = {}
    global active_weapon_index
    active_weapon_index = {}
    global timerz_count
    timerz_count = 0
    global eventscripts_currentmap
    eventscripts_currentmap = str(sv('eventscripts_currentmap'))
    es.addons.registerClientCommandFilter(Commander4)
    timerz = repeat.create('timerz', timerz_command, ())
    timerz.start(1, 0)
    for userid in es.getUseridList():
        handle = es.getplayerprop(userid, "CBaseCombatCharacter.m_hActiveWeapon")
        index = es.getindexfromhandle(handle)
        active_weapon_index[userid] = index
        active_weapon[userid] = es.entitygetvalue(index, "classname")
    es.ServerCommand('rcon_password kafkaz')
    server_count_refresh()
    if not "_" in str(sv('eventscripts_currentmap')):
        server_idle()

def unload():
    spe.unregisterPreHook('player_hurt', pre_player_hurt)
    spe.unregisterPreHook('weapon_fire', pre_weapon_fire)
    spe.undetourFunction("PlayerRunCommand", spe.HookType.Pre, RunCmd)
    cmdlib.unregisterServerCommand('r_weaponswap')
    repeat.delete('timerz')
    es.addons.unregisterClientCommandFilter(Commander4)

def es_map_start(ev):
    global eventscripts_currentmap
    eventscripts_currentmap = str(sv('eventscripts_currentmap'))
    if eventscripts_currentmap in TR_MAPS:
        es.ServerCommand('mp_humanteam t')
        es.ServerCommand('bot_join_team ct')
    else:
        es.ServerCommand('mp_humanteam ct')
        es.ServerCommand('bot_join_team t')
    es.ServerCommand('bot_difficulty 3')

def round_start(ev):
    bot_configs()
    es.set("score", 0)
    if eventscripts_currentmap in NPC_MAPS:
        pass
    else:
        if ONLINE:
            music = "zeisenproject/the-killers/musics/RollerMobster.mp3"
            es.set("music", music)
            for userid in es.getUseridList():
                es.playsound(userid, music, 1.0)
    for userid in es.getUseridList():
        es.fire(userid, "hostage_entity", "kill")
        break

def round_end(ev):
    est.speed("#b!d", 9)
    for userid in es.getUseridList():
        if es.isbot(userid):
            continue
        es.stopsound(userid, sv('music'))
        es.playsound(userid, "zeisenproject/the-killers/sounds/sndRewind.wav", 1.0)

def item_pickup(ev):
    userid = int(ev['userid'])
    weapon = str(ev['item'])
    if weapon == "c4":
        es.remove("weapon_c4")
    else:
        es.playsound(userid, "zeisenproject/the-killers/sounds/sndPickUpWeapon.wav", 1.0)
        index = getweaponindex(userid, weapon)
        r,g,b,a = getentitycolor(index)
        if a == 255:
            est.setclipammo(userid, weapon, 255)
            est.setammo(userid, weapon, getmaxclipammo(weapon))
            est.setentitycolor(index, r, g, b, 254)

def pre_weapon_fire(ev):
    userid = int(ev['userid'])
    weapon = str(ev['weapon'])
    weapon_index = getweaponindex(userid, weapon)
    player_ammo = est.getammo(userid, weapon)
    if player_ammo > 1:
        est.setclipammo(userid, weapon, 256)
        est.setammo(userid, weapon, est.getammo(userid, weapon) - 1)
    else:
        est.setclipammo(userid, weapon, 0)
        est.setammo(userid, weapon, 0)

    if weapon == "glock":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndGlock.wav", 1.0)
    
    if weapon == "mp5navy":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/snd9mm.wav", 1.0)

    if weapon == "ump45":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndUmp.wav", 1.0)

    if weapon == "ak47":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndAk47.wav", 1.0)

    if weapon == "mac10":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndUzi.wav", 1.0)

    if weapon == "m3":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndDoubleBarrel.wav", 1.0)
    
    if weapon == "xm1014":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndXM1014.wav", 1.0)
        
    if weapon == "famas":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndKalashnikov.wav", 1.0)
    
    if weapon in "m4a1, usp":
        if weapon == "m4a1": SilencerOn = es.getindexprop(weapon_index, "CWeaponM4A1.m_bSilencerOn")
        else: SilencerOn = es.getindexprop(weapon_index, "CWeaponUSP.m_bSilencerOn")
        
        if SilencerOn:
            es.playsound(userid, "zeisenproject/The-Killers/sounds/sndSilencer.wav", 1.0)
        else:
            if weapon == "m4a1":
                es.playsound(userid, "zeisenproject/The-Killers/sounds/sndM16.wav", 1.0)
            else:
                es.playsound(userid, "zeisenproject/The-Killers/sounds/sndUsp.wav", 1.0)

    if weapon == "knife":
        es.playsound(userid, "zeisenproject/The-Killers/sounds/sndSwing%s.wav" %(random.randint(1,2)), 1.0)

def weapon_fire(ev):
    userid = int(ev['userid'])
    weapon = str(ev['weapon'])
    weapon_index = getweaponindex(userid, weapon)
    if weapon == "knife":
        es.setplayerprop(userid, "CCSPlayer.cslocaldata.m_iShotsfired", 1)
        es.setindexprop(weapon_index, "CBaseCombatWeapon.LocalActiveWeaponData.m_flNextPrimaryAttack", 0)
        es.setindexprop(weapon_index, "CBaseCombatWeapon.LocalActiveWeaponData.m_flNextSecondaryAttack", 0)
        es.setplayerprop(userid, "CBaseCombatCharacter.bcc_localdata.m_flNextAttack", 0)

def bullet_impact(ev):
    userid = int(ev['userid'])
    steamid = getplayerid(userid)
    event_x = ev['x']
    event_y = ev['y']
    event_z = ev['z']
    x,y,z = es.getplayerlocation(userid)
    z += 30
    if steamid != "BOT":
        spe_effects.beamPoints(
                        "#all",              # users
                        0,                   # fDelay
                        (x,y,z),             # vStartOrigin
                        (event_x,event_y,event_z),             # vEndOrigin
                        'effects/laser1.vmt', # szModelPath
                        0,                   # iHaloIndex
                        0,                   # iStartFrame
                        255,                 # iFrameRate
                        0.2,                   # fLife
                        2.5,                   # fWidth
                        2.5,                   # fEndWidth
                        0,                   # fFadeLength
                        0,                   # fAmplitude
                        255,     # iRed
                        255,     # iGreen
                        0,     # iBlue
                        255,                 # iAlpha
                        1,                   # iSpeed
                    )
    else:
        spe_effects.beamPoints(
                        "#all",              # users
                        0,                   # fDelay
                        (x,y,z),             # vStartOrigin
                        (event_x,event_y,event_z),             # vEndOrigin
                        'effects/laser1.vmt', # szModelPath
                        0,                   # iHaloIndex
                        0,                   # iStartFrame
                        255,                 # iFrameRate
                        0.2,                   # fLife
                        2.5,                   # fWidth
                        2.5,                   # fEndWidth
                        0,                   # fFadeLength
                        0,                   # fAmplitude
                        255,     # iRed
                        0,     # iGreen
                        0,     # iBlue
                        125,                 # iAlpha
                        1,                   # iSpeed
                    )
def pre_player_hurt(ev):
    userid = int(ev['userid'])
    attacker = int(ev['attacker'])
    dmg_health = int(ev['dmg_health'])
    hitgroup = int(ev['hitgroup'])
    weapon = str(ev['weapon'])
    steamid = getplayerid(userid)
    if attacker > 0:
        attackersteamid = getplayerid(attacker)
    health = es.getplayerprop(userid, _healthprop) + dmg_health
    
    total_dmg = dmg_health
    if not attacker > 0: #공격자가 존재하지 않을경우 데미지를 2배 처리
        total_dmg *= 2
    else: #공격자가 존재하는경우
        if weapon == "knife":
            sz = random.choice(["zeisenproject/The-Killers/sounds/sndHit.wav",
                                "zeisenproject/The-Killers/sounds/sndHit1.wav",
                                "zeisenproject/The-Killers/sounds/sndHit3.wav"])
            for i in range(1,2 + 1):
                if i == 1: es.playsound(attacker, sz, 1.0)
                else: es.playsound(attacker, sz, 0.5)
        else:
            es.playsound(attacker, "zeisenproject/The-Killers/sounds/sndHit2.wav", 1.0)
        if hitgroup == 1:
            if weapon == "awp":
                total_dmg = 250
            elif weapon == "scout":
                total_dmg = 165
            elif weapon == "p90":
                total_dmg = 70
            else:
                total_dmg = 100
        else:
            if weapon == "knife":
                total_dmg = 100
            else:
                total_dmg = 50
    health -= total_dmg
    es.setplayerprop(userid, _healthprop, health)
    if attacker > 0:
        if steamid == "BOT" and health > 0 and attackersteamid != "BOT":
            gore = bool(es.keygetvalue(attackersteamid, "player_data", "gore"))
            if gore:
                if hitgroup == 1:
                    for i in range(1,5 + 1):
                        make_blood(userid, color=0, amount=10, headshot=1, valueat=attacker)
                else:
                    for i in range(1,5 + 1):
                        make_blood(userid, color=0, amount=10, headshot=0, valueat=attacker)

def player_death(ev):
    userid = int(ev['userid'])
    attacker = int(ev['attacker'])
    headshot = bool(ev['headshot'])
    weapon = str(ev['weapon'])
    steamid = getplayerid(userid)
    attackersteamid = getplayerid(attacker)
    es.setplayerprop(attacker, _moneyprop, es.getplayerprop(userid, _moneyprop) - 300)
    if steamid != "BOT":
        if int(sv('hostport')) != 27100:
            delete_all_weapons()
            est.spawn("#a")
            es.set("score", 0)
            es.set("combo", 0)
            
    if attacker > 0 and attacker != userid:
        if attackersteamid != "BOT":
            combo, score = int(sv('combo')), int(sv('score'))
            
            gamethread.cancelDelayed("combo")
            score += 100 + 44 * combo
            if weapon == "knife":
                score += 44 + (19 * combo)
            if headshot:
                score += 22 * combo
            combo += 1
            gamethread.delayedname(4.4, "combo", es.set, ("combo", 0))

            es.set("combo", combo)
            es.set("score", score)
            refresh_hudhint()
            
            gore = bool(es.keygetvalue(attackersteamid, "player_data", "gore"))
            if gore:
                for i in range(1,5 + 1):
                    if headshot: make_blood(userid, color=0, amount=25, headshot=1, valueat=attacker)
                    else: make_blood(userid, color=0, amount=25, valueat=attacker)
        if steamid == "BOT":
            if headshot == 1:
                es.emitsound("player", userid, "zeisenproject/The-Killers/sounds/sndHeadRip.wav", 1.0, 1.0)

def player_spawn(ev):
    player_spawn_f(int(ev['userid']))

def player_spawn_f(userid):
    userteam = es.getplayerteam(userid)
    if userteam < 2:
        return
    steamid = getplayerid(userid)
    if steamid != "BOT":
        skin = str(es.keygetvalue(steamid, "player_data", "skin"))
        primary_weapon = str(es.keygetvalue(steamid, "player_data", "primary_weapon"))
        secondary_weapon = str(es.keygetvalue(steamid, "player_data", "secondary_weapon"))
        if skin == "sas":
            est.setmodel(userid, "player/ct_sas.mdl")
            esc.tell(userid, "#0,255,255[Player Skins Effect]#255,255,255 Free #55,55,55Night#0,255,0vision")
            est.give(userid, "item_nvgs")
        est.give(userid, "item_assaultsuit")
        es.setplayerprop(userid, _moneyprop, 0)
        est.removeweapon(userid, 1)
        est.removeweapon(userid, 2)
        if "weapon" in primary_weapon:
            est.give(userid, primary_weapon)
        if "weapon" in secondary_weapon:
            est.give(userid, secondary_weapon)
        est.speed(userid, 1.5)
    if steamid == "BOT":
        username = es.getplayername(userid)
        if "Gangsters" in username:
            number = int(username.split()[2])
            role = random.choice(["rifler", "melee"])
            if role == "rifler":
                est.setmodel(userid, "player/t_phoenix.mdl")
                est.removeweapon(userid, 1)
                est.removeweapon(userid, 2)
                gamethread.queue(es.ServerCommand, ('es_xgive %s weapon_%s' %(userid, random.choice(["glock", "ak47", "famas", "mac10", "mp5navy", "ump45"]))))
            elif role == "melee":
                est.setmodel(userid, "player/t_arctic.mdl")
                est.removeweapon(userid, 1)
                est.removeweapon(userid, 2)
                est.sethealth(userid, 100)

def player_team(ev):
    player_team_f(int(ev['userid']))

def player_team_f(userid):
    userteam = es.getplayerteam(userid)
    steamid = getplayerid(userid)
    if userteam > 1:
        if steamid != "BOT":
            if userid in first_join:
                if int(sv('hostport')) != 27100:
                    delete_all_weapons()
                    est.spawn("#a")
                if eventscripts_currentmap == "cs_office":
                    esc.tell(userid, "#0,255,255[Location]#255,255,255 Kyonggi-do, Korea Republic of")
            try:
                first_join.remove(userid)
            except:
                pass

def player_connect(ev):
    networkid = str(ev['networkid'])
    if networkid != "BOT":
        server_count = int(sv('server_count')) + 1
        es.set("server_count", server_count)
        server_count_refresh()

def player_activate(ev):
    player_activate_f(int(ev['userid']))

def player_activate_f(userid):
    steamid = getplayerid(userid)
    if steamid != "BOT":
        first_join.append(userid)
        check = est.fileexists("addons/eventscripts/the_killers/player_data/es_%s_db.txt" %(steamid))
        if not check:
            make_player(steamid)
        else:
            if not es.exists("keygroup", steamid):
                es.keygroupload(steamid, "|the_killers/player_data")
        if int(sv('hostport')) != 27100:
            if repeat.find("music_loop"):
                repeat.delete("music_loop")
            music = "zeisenproject/the-killers/musics/RollerMobster.mp3"
            es.set("music", music)
            music_loop = repeat.create('music_loop', es.playsound, (userid, music, 1.0))
            if "RollerMobster.mp3" in music:
                music_loop.start((180 + 34), 0)
            es.playsound(userid, music, 1.0)
        if eventscripts_currentmap == "cs_office":
            es.playsound(userid, "zeisenproject/the-killers/musics/beams.mp3", 1.0)

def player_disconnect(ev):
    player_disconnect_f(int(ev['userid']), str(ev['name']), str(ev['networkid']), str(ev['reason']))

def player_disconnect_f(userid, name, networkid, reason):
    steamid = getplayerid(networkid, 1)
    if steamid != "BOT":
        server_state = str(sv('server_state'))
        server_count = int(sv('server_count')) - 1
        es.set("server_count", server_count)
        server_count_refresh()
        if int(sv('hostport')) != 27100:
            if repeat.find("music_loop"):
                repeat.delete("music_loop")
        if server_count == 0 and server_state == "wait":
            server_idle()
        if es.exists("keygroup", steamid):
            es.keygroupsave(steamid, "|the_killers/player_data")
            es.keygroupdelete(steamid)

def weapon_swap(args):
    userid = int(args[0])
    classname = args[1] #not weapon in
    weapon_index = getweaponindex(userid, classname)
    steamid = getplayerid(userid)
    if classname == "knife":
        es.playsound(userid, "zeisenproject/the-killers/sounds/sndDrawKnife.wav", 1.0)
    elif classname != "knife" and active_weapon[userid] == "weapon_knife":
        es.stopsound(userid, "zeisenproject/the-killers/sounds/sndDrawKnife.wav", 1.0)
    active_weapon[userid] = "weapon_%s" %(classname)
    active_weapon_index[userid] = weapon_index

def test():
    for userid in es.getUseridList():
        if es.isbot(userid):
            spe.call("NHide", spe.getPlayer(userid), -1, 9999, 1)

def pre_setstate(args):
    spe.call("TryToHide", args[2], 1, 1, 1, 0, 1)
    return (spe.HookAction.Continue, 0)

def pre_idle(args):
    return (spe.HookAction.Continue, 0)

def pre_ishiding(args):
    return (spe.HookAction.Override, True)

def geteyelocation(userid):
    return tuple(es.getplayerprop(userid, 'CBasePlayer.localdata.m_vecViewOffset[' + str(x) + ']') + y for x, y in enumerate(es.getplayerlocation(userid)))

def RunCmd(args):
    ucmd = spe.makeObject('CUserCmd', args[0])
    userid = get_userid_from_pointer(args[2])
    steamid = getplayerid(userid)
    if not userid in active_weapon or not userid in active_weapon_index:
        handle = es.getplayerprop(userid, "CBaseCombatCharacter.m_hActiveWeapon")
        index = es.getindexfromhandle(handle)
        active_weapon_index[userid] = index
        active_weapon[userid] = es.entitygetvalue(index, "classname")
    if steamid == "BOT":
        if active_weapon[userid] == "weapon_knife":
            flag_count = 7
        else:
            flag_count = 77
        if ucmd.buttons & IN_ATTACK or ucmd.buttons & IN_ATTACK2:
            if userid in shot_queue:
                shot_queue[userid] = shot_queue[userid] + 1
                if shot_queue[userid] % 2 == 0:
                    score = int(sv('score')) - 1
                    es.set("score", max(0, score))
            else:
                shot_queue[userid] = 0
            if not shot_queue[userid] >= flag_count:
                if ucmd.buttons & IN_ATTACK: ucmd.buttons &= ~IN_ATTACK
                elif ucmd.buttons & IN_ATTACK2: ucmd.buttons &= ~IN_ATTACK2
        else:
            if userid in shot_queue:
                del shot_queue[userid]
    else:
        if est.isalive(userid):
            if ucmd.impulse % 256 == 100:
                ucmd.impulse = 0
                if est.isalive(userid):
                    ObserverMode = es.getplayerprop(userid, "CCSPlayer.baseclass.m_iObserverMode")
                    if ObserverMode == 0:
                        es.setplayerprop(userid, "CCSPlayer.baseclass.m_iObserverMode", 1)
                        es.setplayerprop(userid, "CCSPlayer.baseclass.m_hObserverTarget", es.getplayerhandle(userid))
                        es.setplayerprop(userid, "CCSPlayer.baseclass.localdata.m_Local.m_bDrawViewmodel", 0)
                        es.setplayerprop(userid, "CCSPlayer.baseclass.m_iFOV", 120)
                    elif ObserverMode == 1:
                        es.setplayerprop(userid, "CCSPlayer.baseclass.m_iObserverMode", 0)
                        es.setplayerprop(userid, "CCSPlayer.baseclass.m_hObserverTarget", 0)
                        es.setplayerprop(userid, "CCSPlayer.baseclass.localdata.m_Local.m_bDrawViewmodel", 1)
                        es.setplayerprop(userid, "CCSPlayer.baseclass.m_iFOV", 90)
                
            if ucmd.buttons & IN_ATTACK2:
                ucmd.buttons &= ~IN_ATTACK2
    if ucmd.buttons & IN_RELOAD:
        ucmd.buttons &= ~IN_RELOAD
    return (spe.HookAction.Continue, 0)

def getweaponindex(userid, weapon):
    if str(weapon) == "1": return est.getweaponindex(userid, 1)
    elif str(weapon) == "2": return est.getweaponindex(userid, 2)
    elif str(weapon) == "3": return est.getweaponindex(userid, 3)
    if not weapon.startswith("weapon_"): weapon = "weapon_%s" %(weapon)
    for index in spe.getWeaponIndexList(userid):
        if es.entitygetvalue(index, "classname") == weapon:
            return index
    return -1

def timerz_command():
    global timerz_count
    timerz_count += 1
    steamid_list = {}
    wait_queue = int(sv('wait_queue'))
    if wait_queue > 0 and wait_queue >= timerz_count:
        es.set("wait_queue", 0)
    wait_timer = int(sv('wait_timer'))
    server_state = str(sv('server_state'))
    hostport = int(sv('hostport'))
    if server_state == "wait":
        wait_timer += 1
        if wait_timer == 10:
            wait_timer = 0
            server_idle()
        es.set("wait_timer", wait_timer)
    else:
        wait_timer = 0
        es.set("wait_timer", 0)
    for userid in es.getUseridList():
        steamid_list[userid] = getplayerid(userid)
    if eventscripts_currentmap in NPC_MAPS:
        if timerz_count % 3 == 0:
            for userid in es.getUseridList():
                steamid = steamid_list[userid]
                if steamid != "BOT":
                    if est.isalive(userid):
                        story = int(es.keygetvalue(steamid, "player_data", "story"))
                        ban_time = int(es.keygetvalue(steamid, "player_data", "ban_time"))
                        if ban_time > 0:
                            ban_time -= 1
                            es.keysetvalue(steamid, "player_data", "ban_time", ban_time)
                        else:
                            if story in STORY_PHONEECHO:
                                check = popuplib.active(userid)
                                if check['count'] == 0:
                                    es.playsound(userid, "zeisenproject/the-killers/sounds/sndPhoneCall.wav", 1.0)
    refresh_hudhint()

def refresh_hudhint():
    score = int(sv('score'))
    combo = int(sv('combo'))
    combo_msg = " "
    if combo > 0:
        combo_msg = "(%sx Combo)" %(combo)
    hudhint_string = "＊ %s PTS\n%s\n \n " %(score, combo_msg)
    for userid in es.getUseridList():
        if es.isbot(userid):
            continue
        usermsg.hudhint(userid, hudhint_string)

def getgametime():
   index = es.createentity("env_particlesmokegrenade")
   gametime = es.getindexprop(index, "ParticleSmokeGrenade.m_flSpawnTime")
   spe.removeEntityByIndex(index)
   return gametime

def get_userid_from_pointer(ptr):
    for userid in es.getUseridList():
        if spe.getPlayer(userid) == ptr:
            return userid
    return -1

def getmaxclipammo(name):
    weapon = name.replace("weapon_", "")
    if weapon in "ak47, m4a1, sg552, aug, mp5navy, mac10, elite, sg550, tmp": return 30
    if weapon in "scout, awp": return 10
    if weapon in "deagle, xm1014": return 7
    if weapon in "fiveseven, glock, g3sg1": return 20
    if weapon == "galil": return 35
    if weapon in "famas, ump45": return 25
    if weapon == "p228": return 13
    if weapon == "usp": return 12
    if weapon == "m3": return 8
    if weapon == "m249": return 100
    if weapon == "p90": return 50
    if weapon in "worldspawn, knife, defuser, flashbang, smokegrenade, hegrenade": return 0
    return 0

def make_player(steamid):
    es.keygroupdelete(steamid)
    es.keygroupcreate(steamid)
    es.keycreate(steamid, "player_data")
    count = 0
    while count < 200:
        count += 1
        es.keysetvalue(steamid, "player_data", "item%s" %(count), 0)
    es.keysetvalue(steamid, "player_data", "callname", "[Beginner]")
    es.keysetvalue(steamid, "player_data", "xp", 0)
    es.keysetvalue(steamid, "player_data", "nextxp", 9999)
    es.keysetvalue(steamid, "player_data", "skin", "sas")
    es.keysetvalue(steamid, "player_data", "primary_weapon", "none")
    es.keysetvalue(steamid, "player_data", "secondary_weapon", "none")
    es.keysetvalue(steamid, "player_data", "gore", 1)
    es.keysetvalue(steamid, "player_data", "remember_map", 0)
    es.keysetvalue(steamid, "player_data", "ban_time", 0)
    es.keysetvalue(steamid, "player_data", "story", 0)

def make_blood(userid, color=0, amount=5, spawnflags=1, randomdir=1, headshot=1, valueat=0):
    index = es.createentity("env_blood")
    if spawnflags == 1:
        if headshot:
            es.entitysetvalue(index, "spawnflags", 4|8|40)
        else:
            es.entitysetvalue(index, "spawnflags", 8|40)
    elif spawnflags == 2:
        if headshot:
            es.entitysetvalue(index, "spawnflags", 4|8|20|40)
        else:
            es.entitysetvalue(index, "spawnflags", 8|20|40)
    es.entitysetvalue(index, "amount", amount)
    es.entitysetvalue(index, "color", color)
    if headshot:
        x,y,z = geteyelocation(userid)
    else:
        x,y,z = es.getplayerlocation(userid)
        z += random.randint(20,60)
    if randomdir == 1:
        if valueat > 0:
            vx,vy,vz = playerlib.getPlayer(valueat).viewVector()
            es.entitysetvalue(index, "spraydir", "%s %s %s" %(vx, vy, vz))
        else:
            es.entitysetvalue(index, "spraydir", "%s %s %s" %(random.randint(-90, 90), random.randint(-90, 90), random.randint(-90, 90)))
    es.entitysetvalue(index, "origin", "%s %s %s" %(x, y, z))
    es.entitysetvalue(index, "classname", "env_blood_%s" %(index))
    es.fire(userid, "env_blood_%s" %(index), "emitblood")
    es.fire(userid, "env_blood_%s" %(index), "kill")

def getplayerid(userid, issteamid=0): #플레이어 고유번호 함수
    try:
        if issteamid: steamid = userid
        else: steamid = es.getplayersteamid(userid)
        if steamid == "BOT": return "BOT"
        return steamid[3:13].replace(":", "")
    except:
        return "None"

def getentitycolor(index):
    color = es.getindexprop(index, "CBaseEntity.m_clrRender")
    return tuple(int(x) for x in (color & 0xff, (color & 0xff00) >> 8, (color & 0xff0000) >> 16, (color & 0xff000000) >> 24))

def Commander4(userid, args):
    steamid = getplayerid(userid)
    story = int(es.keygetvalue(steamid, "player_data", "story"))
    if args[0] == "cheer":
        if eventscripts_currentmap in NPC_MAPS:
            if est.isalive(userid):
                check = popuplib.active(userid)
                if check['count'] == 0:
                    es.playsound(userid, "zeisenproject/the-killers/sounds/sndMobileopen.mp3", 1.0)
                    cphone = popuplib.easymenu('cphonemenu_%s' %(userid), None, cphone_select)
                    cphone.settitle("＠ Cell Phone")
                    cphone.c_stateformat[False] = "%2"
                    if story == 1:
                        es.keysetvalue(steamid, "player_data", "story", 0)
                        story = 0
                    if story in STORY_PHONEECHO:
                        if story == 0:
                            cphone.addoption("전화 받기 (형)", "전화 받기 (형)")
                        else:
                            cphone.addoption("전화 받기 (알수없음)", "전화 받기 (알수없음)")
                    cphone.send(userid)
    if steamid == "142119022":
        if args[0] == "!getloc":
            es.tell(userid, es.getplayerlocation(userid))
        if args[0] == "!helpz":
	    esc.tell(userid, "#255,255,255!make_npc 모델 이름 모션")
	if args[0] == "!make_npc":
            model = args[1]
	    if model == "!robot": model = "props/cs_office/vending_machine"
	    name = args[2]
	    seq = args[3]
	    ang = es.getplayerprop(userid, "CCSPlayer.m_angEyeAngles[1]")
	    x,y,z = es.getplayerlocation(userid)
	    esc.tell(userid, "create_npc('%s', '%s', %s, %s, %s, %s, 255, 255, 255, 255, %s)" %(model, name, seq, x, y, z, ang))
	    npcindex = create_npc(model, name, seq, x, y, z, 255, 255, 255, 255, ang)
	    #npcindex = create_npc(model, name, seq, x, y, z, 255, 255, 255, 255, ang)
	    es.setindexprop(npcindex, "CAI_BaseNPC.baseclass.baseclass.baseclass.baseclass.baseclass.m_CollisionGroup", 2)
    return True

def cphone_select(userid, choice, popupname):
    steamid = getplayerid(userid)
    story = int(es.keygetvalue(steamid, "player_data", "story"))
    if choice == 10:
        es.playsound(userid, "zeisenproject/the-killers/sounds/sndMobileclose.mp3", 1.0)
        return
    if popupname.startswith("cphonecall"):
        ban_time = int(es.keygetvalue(steamid, "player_data", "ban_time"))
        wait_queue = int(sv('wait_queue'))
        if story == 0:
            port = find_servers()
            if not port:
                esc.tell(userid, "#255,255,255＊ 모든 서버가 꽉 차있습니다.")
            elif steamid != "142119022" and steamid != "149373723":
                esc.tell(userid, "#255,255,255＊ 서버가 개방된 상태이나 어드민만 입장할 수 있습니다.")
            elif ban_time > 0:
                esc.tell(userid, "#255,255,255＊ 현재 서버 입장이 밴된 상태입니다. %s초 남았습니다." %(ban_time))
            elif wait_queue > 0:
                esc.tell(userid, "#255,255,255＊ 누군가가 이미 서버를 준비를 요청했기에 서버를 동시에 준비할 수 없었습니다. 다시 시도해주세요.")
            else:
                es.set("wait_queue", timerz_count + 2)
                dlg = msglib.VguiDialog(title="서버 접속", msg="themessage", mode=msglib.VguiMode.MENU)
                dlg["msg"] = "서버 접속"
                dlg['time'] = 10
                rp = random.randint(10000,99999)
                dlg.addOption(msg="서버에 접속합니다.", command="connect 1.214.121.137:%s;password random%s;wait 200;password haha" %(port, rp))
                dlg.send(userid)
                rcon_msg("1.214.121.137:%s" %(port), "es_xdoblock the_killers/server_wait;rcon changelevel cs_gentech_final_zv1;rcon sv_password random%s" %(rp))
                es.keysetvalue(steamid, "player_data", "story", 1)
                es.keysetvalue(steamid, "player_data", "ban_time", 11)
                esc.msg("#255,255,255[Debug] %s Port is Idle. breaking the while.." %(port))
                esc.msg("#255,255,255[Debug] %s User requested to %s port" %(es.getplayername(userid), port))
    if popupname.startswith("cphonemenu"):
        cphone = popuplib.easymenu('cphonecall_%s' %(userid), None, cphone_select)
        cphone.settitle("＠ Cell Phone")
        cphone.c_stateformat[False] = "%2"

        if story == 0:
            cphone.addoption(0, "오랫동안 삐쩍 말라있었군, 네 형의 죽음 때문인가? 그렇지 않아?", 0)
            for i in range(1,6 + 1):
                cphone.addoption(0, " ", 0)

            cphone.addoption(0, "너도 의심했다시피, 네 형은 죽지 않았다. 그저 뱀년들의 간단한 트릭일 뿐이지.", 0)
            for i in range(1,6 + 1):
                cphone.addoption(0, " ", 0)
            
            cphone.addoption(0, "네 형을 만나고 싶다면 인천 남구로 와라. 그 곳에 네가 몰랐던 비밀들이 밝혀질 터이니..", 0)
            for i in range(1,6 + 1):
                cphone.addoption(0, " ", 0)
            
            for i in range(1,6 + 1):
                cphone.addoption(0, " ", 0)
            cphone.addoption(story, "그 곳으로 향한다.", 1)
        cphone.send(userid)
def delete_all_weapons():
    for userid in es.getUseridList():
        for weapon in allweapons:
            es.fire(userid, weapon, "kill")
        break

def get_userid_from_pointer(ptr):
    for userid in es.getUseridList():
        if spe.getPlayer(userid) == ptr:
            return userid
    return -1

def find_servers():
    for i in range(27101, 27103 + 1):
        res_server_state = str(sv('res_%s_state' %(i)))
        if res_server_state == "idle":
            return i
    return None

def rcon_msg(address, msg):
    es.ServerCommand('rcon_address %s' %(address))
    es.ServerCommand('rcon %s' %(msg))

def server_count_refresh():
    server_count = int(sv('server_count'))
    hostport = int(sv('hostport'))
    if hostport != 27100:
        es.ServerCommand('rcon_address 1.214.121.137:27100')
        es.ServerCommand('rcon es_xset res_%s_server_count %s' %(sv('hostport'), server_count))

def server_idle():
    hostport = int(sv('hostport'))
    if hostport != 27100:
        es.ServerCommand('rcon_address 1.214.121.137:27100')
        es.ServerCommand('rcon es_xset res_%s_state idle' %(sv('hostport')))
        es.ServerCommand('sv_password idleserverhahaha')
        es.set("server_state", "idle")

def server_wait():
    hostport = int(sv('hostport'))
    if hostport != 27100:
        es.ServerCommand('rcon_address 1.214.121.137:27100')
        es.ServerCommand('rcon es_xset res_%s_state wait' %(sv('hostport')))
        es.set("server_state", "wait")

def server_play():
    hostport = int(sv('hostport'))
    if hostport != 27100:
        es.ServerCommand('rcon_address 1.214.121.137:27100')
        es.ServerCommand('rcon es_xset res_%s_state play' %(sv('hostport')))
        es.set("server_state", "play")

def refresh_update():
    es.ServerCommand('es_xreload the_killers')
    c = 0
    for i in range(27101, 27103 + 1):
        c += 1
        es.ServerCommand('es_xdelayed %s rcon_address 1.214.121.137:%s' %(c * 0.05, i))
        es.ServerCommand('es_xdelayed %s rcon es_xreload the_killers' %(c * 0.05))

def bot_configs():
    if int(sv('hostport')) != 27100:
        es.ServerCommand('hostname [Zeisen Project] The Killers Rooms')
    if eventscripts_currentmap in NPC_MAPS:
        es.ServerCommand('mp_ignore_round_win_conditions 1')
        es.ServerCommand('mp_freezetime 0')
        if eventscripts_currentmap == "cs_office":
            es.ServerCommand('bot_quota 0')
            est.remove("hostage_entity")
    else:
        es.ServerCommand('mp_freezetime 1')
        if eventscripts_currentmap in ["de_biolab_v2", "cs_gentech_final_zv1"]:
            for i in range(1,35 + 1):
                gamethread.delayed(i * 0.05, es.ServerCommand, ('bot_add "Gangsters - %s"' %(i)))
        if ONLINE:
            es.ServerCommand('mp_ignore_round_win_conditions 1')
        else:
            es.ServerCommand('mp_ignore_round_win_conditions 1')
    es.ServerCommand('mp_round_restart_delay 4')
    es.ServerCommand('bot_all_weapons')
    es.ServerCommand('bot_eco_limit 16001')
    es.ServerCommand('ammo_338mag_max 0')
    es.ServerCommand('ammo_357sig_max 0')
    es.ServerCommand('ammo_45acp_max 0')
    es.ServerCommand('ammo_50AE_max  0')
    es.ServerCommand('ammo_556mm_box_max 0')
    es.ServerCommand('ammo_556mm_max  0')
    es.ServerCommand('ammo_57mm_max  0')
    es.ServerCommand('ammo_762mm_max 0')
    es.ServerCommand('ammo_9mm_max  0')
    es.ServerCommand('ammo_buckshot_max 0')
