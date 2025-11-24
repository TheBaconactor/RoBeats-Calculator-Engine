-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.MissionType)
require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_13 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_15 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_16 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_17 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_18 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_19 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_20 = require(game.ReplicatedStorage.Pets.PetUtils)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
v21:require_client(function() --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (ref 3): v_u_24 ]]
    v_u_22 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
end)
local v_u_35 = {
    ["EventMission"] = {
        ["RBBattleMission1"] = "RBBattleMission1",
        ["RBBattleMission2"] = "RBBattleMission2",
        ["RBBattleMission3"] = "RBBattleMission3",
        ["RBBattleSpecialStage1"] = "RBBattleSpecialStage1",
        ["RBBattleSpecialStage2"] = "RBBattleSpecialStage2",
        ["RBBattleSpecialStage3"] = "RBBattleSpecialStage3",
        ["SongLaunchSpecialEvent"] = "SongLaunchSpecialEvent",
        ["SongLaunchBonusNPCEvent"] = "SongLaunchBonusNPCEvent",
        ["ArtistEvent"] = "ArtistEvent",
        ["TowerHeroesEvent"] = "TowerHeroesEvent",
        ["RobeatsBirthdayEvent"] = "RobeatsBirthdayEvent",
        ["GoldnEvent"] = "GoldnEvent",
        ["GenericArtistEvent"] = "GenericArtistEvent",
        ["GenericArtistP2Event"] = "GenericArtistP2Event",
        ["GenericArtistP3Event"] = "GenericArtistP3Event",
        ["Black17Event"] = "Black17Event"
    },
    ["push_eventmission_match_end_menu"] = function(_, p25, p26) --[[ Name: push_eventmission_match_end_menu ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_24, (ref 3): v_u_22 ]]
        if typeof(p26) == "table" then
            if p26.ShowSongAcquiredPopup == true and v_u_18:singleton():contains_key(p26.AcquiredSongKey) then
                p25._menus:push_menu(v_u_24:new(p25, p25._spui, p25._menus, p26.AcquiredSongKey))
            end;
            if typeof(p26.PopupMessageTitle) == "string" and typeof(p26.PopupMessageBody) == "string" then
                p25._menus:push_menu(v_u_22:new(p25, p25._spui, p25._menus):set_text(p26.PopupMessageTitle, p26.PopupMessageBody))
            end;
        end;
    end,
    ["test_playerblob_can_claim_song_launch_claimed_id"] = function(_, p27, p28) --[[ Name: test_playerblob_can_claim_song_launch_claimed_id ]] --[[ Line: 90 ]]
        return p27.SongLaunchClaimedID < p28;
    end,
    ["playerblob_claim_song_launch_claimed_id"] = function(_, p29, p30) --[[ Name: playerblob_claim_song_launch_claimed_id ]] --[[ Line: 98 ]]
        p29.SongLaunchClaimedID = p30
    end,
    ["update_player_event_data"] = function(_, _) end,
    ["get_24kgoldn_eventmission_info"] = function(_, _) --[[ Name: get_24kgoldn_eventmission_info ]] --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return v_u_18:invalid_songkey();
    end,
    ["is_24kgoldn_event_active"] = function(_, _) --[[ Name: is_24kgoldn_event_active ]] --[[ Line: 224 ]]
        return false;
    end,
    ["get_24kgoldn_event_playable_song_set"] = function(_) --[[ Name: get_24kgoldn_event_playable_song_set ]] --[[ Line: 234 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({ 1261, 1262, 1263 });
    end,
    ["get_24kgoldn_pet_id"] = function(_) --[[ Name: get_24kgoldn_pet_id ]] --[[ Line: 240 ]]
        return 12;
    end,
    ["get_24kgoldn_gear_id"] = function(_) --[[ Name: get_24kgoldn_gear_id ]] --[[ Line: 241 ]]
        return 167;
    end,
    ["get_24kgoldn_hunt_npc_ids_set"] = function(_) --[[ Name: get_24kgoldn_hunt_npc_ids_set ]] --[[ Line: 243 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10
        });
    end,
    ["is_birthday_event_active"] = function(_, _) --[[ Name: is_birthday_event_active ]] --[[ Line: 297 ]]
        return false;
    end,
    ["get_birthday_event_song_launch_claimed_id"] = function(_) --[[ Name: get_birthday_event_song_launch_claimed_id ]] --[[ Line: 307 ]]
        return 33;
    end,
    ["get_birthday_event_fever_icon_material"] = function(_) --[[ Name: get_birthday_event_fever_icon_material ]] --[[ Line: 308 ]]
        return 173;
    end,
    ["get_birthday_event_dance_id"] = function(_) --[[ Name: get_birthday_event_dance_id ]] --[[ Line: 309 ]]
        return 220;
    end,
    ["get_birthday_event_pet_id"] = function(_) --[[ Name: get_birthday_event_pet_id ]] --[[ Line: 310 ]]
        return 10;
    end,
    ["get_birthday_event_playable_song_set"] = function(_) --[[ Name: get_birthday_event_playable_song_set ]] --[[ Line: 312 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({
            1041,
            1042,
            1221,
            1222,
            465,
            466,
            1214,
            1215,
            1250,
            1251
        });
    end,
    ["is_tower_heroes_event_active"] = function(_, _) --[[ Name: is_tower_heroes_event_active ]] --[[ Line: 324 ]]
        return false;
    end,
    ["tower_heroes_get_playable_song_set"] = function(_) --[[ Name: tower_heroes_get_playable_song_set ]] --[[ Line: 334 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({
            1178,
            1179,
            1180,
            1181,
            1182,
            1183,
            1184,
            1185,
            1186,
            1187,
            1188,
            1189
        });
    end,
    ["get_pet1_id"] = function(_) --[[ Name: get_pet1_id ]] --[[ Line: 372 ]]
        return 4;
    end,
    ["get_pet2_id"] = function(_) --[[ Name: get_pet2_id ]] --[[ Line: 373 ]]
        return 5;
    end,
    ["playerblob_get_rb_battles_challenge_active"] = function(_, _, p31) --[[ Name: playerblob_get_rb_battles_challenge_active ]] --[[ Line: 435 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_14 ]]
        if p31 ~= nil then
            return p31:is_event_type_active(v_u_14.EventType.RBChallenge);
        end;
        v_u_4:warnf("SpecialEventInfo day_event_list is nil")
        return false;
    end,
    ["playerblob_get_rb_battles_swordhunt_active"] = function(_, _, p32) --[[ Name: playerblob_get_rb_battles_swordhunt_active ]] --[[ Line: 440 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_14 ]]
        if p32 ~= nil then
            return p32:is_event_type_active(v_u_14.EventType.RBSwordHunt);
        end;
        v_u_4:warnf("SpecialEventInfo day_event_list is nil")
        return false;
    end,
    ["get_rbbattle_special_stage1_danceid"] = function(_) --[[ Name: get_rbbattle_special_stage1_danceid ]] --[[ Line: 472 ]]
        return 160;
    end,
    ["get_rbbattle_special_stage3_titleid"] = function(_) --[[ Name: get_rbbattle_special_stage3_titleid ]] --[[ Line: 473 ]]
        return 18;
    end,
    ["equipped_dict_ok"] = function(_, p33) --[[ Name: equipped_dict_ok ]] --[[ Line: 613 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_16 ]]
        local v34 = v_u_15:playerblob_slot_to_equippedobj_dict(p33)
        if v34:contains(v_u_16.BACK) == true then
            return v_u_15:playerblob_ownedid_to_equipmentid(p33, v34:get(v_u_16.BACK).OwnedID) == 67;
        else
            return false;
        end;
    end
}
v_u_35.get_event_mission_display_info = function(_, p36) --[[ Name: get_event_mission_display_info ]] --[[ Line: 58 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_35, (copy 3): v_u_18 ]]
    if v_u_2:test_enum_member(p36:get_event_info(), v_u_35.EventMission) == true then
        local v37, v38, v39, v40, v41 = v_u_35:get_24kgoldn_eventmission_info(p36)
        if v37 == v_u_18:invalid_songkey() then
            return v_u_18:invalid_songkey();
        else
            return v37, v38, v39, v40, v41;
        end;
    else
        return v_u_18:invalid_songkey();
    end;
end;
local v_u_42 = true
v_u_35.server_startup = function(_) --[[ Name: server_startup ]] --[[ Line: 108 ]]
    --[[ Upvalues: (ref 1): v_u_42 ]]
    v_u_42 = false
end;
v_u_35.client_startup = function(_) --[[ Name: client_startup ]] --[[ Line: 112 ]]
    --[[ Upvalues: (ref 1): v_u_42 ]]
    v_u_42 = true
end;
local v_u_43 = false
v_u_35.get_24kgoldn_has_badge = function(_) --[[ Name: get_24kgoldn_has_badge ]] --[[ Line: 119 ]]
    --[[ Upvalues: (ref 1): v_u_43 ]]
    return v_u_43;
end;
v_u_35.update_24kgoldn_player_event_data = function(_, p44) --[[ Name: update_24kgoldn_player_event_data ]] --[[ Line: 121 ]]
    --[[ Upvalues: (ref 1): v_u_43 ]]
    if typeof(p44) == "table" and p44.GoldnHasBadge == true then
        v_u_43 = true
    end;
end;
local v_u_45 = 0
v_u_35.get_24kgoldn_playcount = function(_) --[[ Name: get_24kgoldn_playcount ]] --[[ Line: 131 ]]
    --[[ Upvalues: (ref 1): v_u_45 ]]
    return v_u_45;
end;
v_u_35.push_24kgoldn_eventmission_match_end_menu = function(_, _, p46) --[[ Name: push_24kgoldn_eventmission_match_end_menu ]] --[[ Line: 133 ]]
    --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_43 ]]
    if typeof(p46) == "table" then
        if typeof(p46.GoldnPlayCount) == "number" then
            v_u_45 = p46.GoldnPlayCount
        end;
        if p46.GoldnHasBadge == true then
            v_u_43 = true
        end;
    end;
end;
v_u_35.get_24kgoldn_playerblob_has_claimed_pet = function(_, p47) --[[ Name: get_24kgoldn_playerblob_has_claimed_pet ]] --[[ Line: 249 ]]
    --[[ Upvalues: (copy 1): v_u_20, (copy 2): v_u_35 ]]
    return v_u_20:playerblob_can_add_pet_of_petid(p47, v_u_35:get_24kgoldn_pet_id()) ~= true;
end;
local v_u_48 = v_u_1:new()
v_u_35.get_24kgoldn_claimed_hunt_ids_set = function(_) --[[ Name: get_24kgoldn_claimed_hunt_ids_set ]] --[[ Line: 254 ]]
    --[[ Upvalues: (copy 1): v_u_48 ]]
    return v_u_48;
end;
v_u_35.get_24kgoldn_playerblob_has_claimed_gear = function(_, p49) --[[ Name: get_24kgoldn_playerblob_has_claimed_gear ]] --[[ Line: 258 ]]
    --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_35 ]]
    return v_u_15:playerblob_get_first_ownedid_of_equipmentid(p49, v_u_35:get_24kgoldn_gear_id()) ~= nil;
end;
v_u_35.is_24kgoldn_pet_equipped = function(_, p50) --[[ Name: is_24kgoldn_pet_equipped ]] --[[ Line: 262 ]]
    --[[ Upvalues: (copy 1): v_u_20, (copy 2): v_u_35 ]]
    for _, v51 in v_u_20:playerblob_get_slot_to_owned_pet_dict(p50):key_itr() do
        if v_u_20:ownedpet_get_petid(v51) == v_u_35:get_24kgoldn_pet_id() then
            return true;
        end;
    end;
    return false;
end;
v_u_35.is_24kgoldn_gear_equipped = function(_, p52) --[[ Name: is_24kgoldn_gear_equipped ]] --[[ Line: 270 ]]
    --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_16, (copy 3): v_u_35 ]]
    local v53 = v_u_15:playerblob_slot_to_equippedobj_dict(p52)
    if v53:contains(v_u_16.HAT) == true then
        return v_u_15:playerblob_ownedid_to_equipmentid(p52, v53:get(v_u_16.HAT).OwnedID) == v_u_35:get_24kgoldn_gear_id();
    else
        return false;
    end;
end;
v_u_35.tower_heroes_get_claim_song_set = function(_) --[[ Name: tower_heroes_get_claim_song_set ]] --[[ Line: 341 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_35, (copy 3): v_u_18, (copy 4): v_u_19 ]]
    local v54 = v_u_1:new()
    for v55, _ in v_u_35:tower_heroes_get_playable_song_set():key_itr() do
        if v_u_18:singleton():key_get_audiomod(v55) == v_u_19.Normal then
            v54:add_set(v55)
        end;
    end;
    return v54;
end;
v_u_35.tower_heroes_get_songkey_grant_target_songkey = function(_, p56) --[[ Name: tower_heroes_get_songkey_grant_target_songkey ]] --[[ Line: 351 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_18, (copy 3): v_u_19 ]]
    if v_u_35:tower_heroes_get_playable_song_set():contains(p56) ~= true then
        return false, v_u_18:invalid_songkey();
    end;
    for v57, _ in v_u_18:singleton():get_all_modes_of_songkey(p56):key_itr() do
        if v_u_18:singleton():key_get_audiomod(v57) == v_u_19.Normal then
            return true, v57;
        end;
    end;
    return false, v_u_18:invalid_songkey();
end;
v_u_35.tower_heroes_playerblob_get_claim_song_count = function(_, p58) --[[ Name: tower_heroes_playerblob_get_claim_song_count ]] --[[ Line: 362 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_5 ]]
    local v59 = 0
    for v60, _ in v_u_35:tower_heroes_get_claim_song_set():key_itr() do
        if v_u_5:get_song_key_owned_count(p58, v60) > 0 then
            v59 = v59 + 1
        end;
    end;
    return v59;
end;
local v_u_64 = {
    ["new"] = function(_, p61, p62, p63) --[[ Name: new ]] --[[ Line: 378 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22:new(p61, p62, p63, game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.RBBattleEventMessageUI:Clone());
    end
}
v_u_35.rb_battles_push_eventmission_match_end_menu = function(_, p_u_65, p66) --[[ Name: rb_battles_push_eventmission_match_end_menu ]] --[[ Line: 388 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_64, (ref 3): v_u_22, (copy 4): v_u_13, (copy 5): v_u_10 ]]
    v_u_2:is_table(p66)
    if p66.ShowSpecialEventMissionPopup == true then
        if p66.RBBattlesPopup == true then
            p_u_65._menus:push_menu(v_u_64:new(p_u_65, p_u_65._spui, p_u_65._menus):set_text(p66.Header, p66.Text))
        else
            p_u_65._menus:push_menu(v_u_22:new(p_u_65, p_u_65._spui, p_u_65._menus):set_text(p66.Header, p66.Text))
        end;
    end;
    local v_u_67 = nil
    if p66.SpecialStage == nil then
        if p66.ErrorMessage ~= nil then
            v_u_67 = p66.ErrorMessage
        end;
    else
        local l_SpecialStage_0 = p66.SpecialStage
        v_u_67 = l_SpecialStage_0 == 4 and "You feel as if a great secret has been revealed. But where? Look around!" or (l_SpecialStage_0 == 3 and "You feel as if you are right on the cusp of a great discovery..." or (l_SpecialStage_0 == 2 and "You feel as if you are getting closer to your destination..." or "You feel as if a hidden sequence of events has been set in motion..."))
    end;
    if v_u_67 ~= nil then
        p_u_65._update_enqueue_fn:enqueue_function(function() --[[ Line: 419 ]]
            --[[ Upvalues: (copy 1): p_u_65, (ref 2): v_u_13, (ref 3): v_u_67 ]]
            local v68 = p_u_65._chat:get_game_instance_channel()
            if v68 == nil then
                p_u_65._chat:get_system_channel():add_message_to_channel(v_u_13:new(v_u_67))
            else
                v68:add_message_to_channel(v_u_13:new(v_u_67))
            end;
        end, v_u_10:DeltaTimeToTimescale(1.5))
    end;
end;
local function _(_) --[[ Name: playerblob_is_tester ]] --[[ Line: 430 ]]
    return false;
end;
v_u_35.push_eventmission_start_menu = function(_, p_u_69, p_u_70) --[[ Name: push_eventmission_start_menu ]] --[[ Line: 446 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_35, (copy 3): v_u_3, (copy 4): v_u_17, (copy 5): v_u_64, (ref 6): v_u_23 ]]
    v_u_2:is_enum_member(p_u_70, v_u_35.EventMission)
    local v_u_71, v72, v73, v74, v75 = v_u_35:get_eventmission_info(p_u_70)
    p_u_69._menus:push_menu(v_u_64:new(p_u_69, p_u_69._spui, p_u_69._menus):set_text(v75, (v_u_3:get_mission_description_text({
        ["Type"] = v72,
        ["Count"] = v73,
        ["PlayersRequired"] = v74,
        ["TargetSong"] = v_u_71,
        ["Difficulty"] = v_u_17.Beginner
    }))):set_okay_button_fn(function() --[[ Line: 461 ]]
        --[[ Upvalues: (copy 1): p_u_69, (copy 2): p_u_70, (ref 3): v_u_23, (copy 4): v_u_71 ]]
        local v76 = p_u_69._lobby_join:get_lobby()
        v76._game_join_protocol:set_event_info(p_u_70)
        p_u_69._menus:push_menu(v_u_23:new(v76, p_u_69._spui, p_u_69._menus, v_u_71, nil))
    end))
end;
v_u_35.playerblob_get_specialevent_stage_active = function(_, p77, p78) --[[ Name: playerblob_get_specialevent_stage_active ]] --[[ Line: 475 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_6 ]]
    if p78 == v_u_35.EventMission.RBBattleSpecialStage1 then
        return v_u_6:get_owned_danceid_to_equipped_dict(p77):contains(v_u_35:get_rbbattle_special_stage1_danceid());
    else
        return false;
    end;
end;
v_u_35.rbbattle_special_stage1_init = function(_, p_u_79, p_u_80) --[[ Name: rbbattle_special_stage1_init ]] --[[ Line: 484 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (copy 3): v_u_7, (copy 4): v_u_10, (ref 5): v_u_22, (copy 6): v_u_11, (copy 7): v_u_12, (copy 8): v_u_35 ]]
    local v81 = {}
    local v_u_82 = v_u_9:new():push_back_table_list({
        v_u_8.KEY_UP,
        v_u_8.KEY_DOWN,
        v_u_8.KEY_LEFT,
        v_u_8.KEY_RIGHT,
        v_u_8.KEY_A,
        v_u_8.KEY_B
    })
    local v_u_83 = v_u_9:new():push_back_table_list({
        v_u_8.KEY_UP,
        v_u_8.KEY_UP,
        v_u_8.KEY_DOWN,
        v_u_8.KEY_DOWN,
        v_u_8.KEY_LEFT,
        v_u_8.KEY_RIGHT,
        v_u_8.KEY_LEFT,
        v_u_8.KEY_RIGHT,
        v_u_8.KEY_B,
        v_u_8.KEY_A
    })
    local v_u_84 = v_u_9:new()
    local v_u_85 = true
    local v_u_86 = -1
    v81.cons = function(p87) --[[ Name: cons ]] --[[ Line: 513 ]]
        --[[ Upvalues: (copy 1): p_u_80 ]]
        p_u_80.Visible = true
        p87:set_display_alpha(0.025)
    end;
    v81.set_display_alpha = function(_, p88) --[[ Name: set_display_alpha ]] --[[ Line: 518 ]]
        --[[ Upvalues: (ref 1): v_u_86, (copy 2): p_u_80, (ref 3): v_u_7 ]]
        v_u_86 = p88
        p_u_80.ImageTransparency = v_u_7:tra(p88)
    end;
    v81.set_disabled = function(_) --[[ Name: set_disabled ]] --[[ Line: 523 ]]
        --[[ Upvalues: (ref 1): v_u_85, (copy 2): p_u_80 ]]
        v_u_85 = false
        p_u_80.Visible = false
    end;
    local function f_mobile_key_pressed(p89) --[[ Name: mobile_key_pressed ]] --[[ Line: 528 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8 ]]
        local v90 = v_u_7:get_cursor_nxy()
        if p89 == v_u_8.KEY_UP then
            return v90.Y < 0.1;
        end;
        if p89 == v_u_8.KEY_DOWN then
            return v90.Y > 0.9;
        end;
        if p89 == v_u_8.KEY_LEFT then
            return v90.X < 0.1;
        end;
        if p89 == v_u_8.KEY_RIGHT then
            return v90.X > 0.9;
        end;
        if p89 == v_u_8.KEY_B then
            local v91
            if v90.X > 0.3 and (v90.X < 0.45 and v90.Y > 0.4) then
                v91 = v90.Y < 0.6
            else
                v91 = false
            end;
            return v91;
        end;
        if p89 ~= v_u_8.KEY_A then
            return false;
        end;
        local v92
        if v90.X > 0.55 and (v90.X < 0.7 and v90.Y > 0.4) then
            v92 = v90.Y < 0.6
        else
            v92 = false
        end;
        return v92;
    end;
    local function f_mobile_any_key_pressed() --[[ Name: mobile_any_key_pressed ]] --[[ Line: 548 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        local v93 = v_u_7:get_cursor_nxy()
        local v94
        if v93.Y < 0.1 or (v93.Y > 0.9 or (v93.X < 0.1 or (v93.X > 0.9 or v93.X > 0.3 and (v93.X < 0.45 and (v93.Y > 0.4 and v93.Y < 0.6))))) then
            v94 = true
        elseif v93.X > 0.55 and (v93.X < 0.7 and v93.Y > 0.4) then
            v94 = v93.Y < 0.6
        else
            v94 = false
        end;
        return v94;
    end;
    v81.behaviour_update = function(p95, p96) --[[ Name: behaviour_update ]] --[[ Line: 553 ]]
        --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_10, (ref 3): v_u_86, (copy 4): v_u_82, (copy 5): p_u_79, (ref 6): v_u_7, (ref 7): v_u_8, (copy 8): f_mobile_any_key_pressed, (copy 9): v_u_84, (copy 10): v_u_83, (copy 11): f_mobile_key_pressed, (ref 12): v_u_22, (ref 13): v_u_11, (ref 14): v_u_12, (ref 15): v_u_35 ]]
        if v_u_85 ~= true then
            return;
        end;
        p95:set_display_alpha(v_u_10:expt_sec(v_u_86, 0.025, 0.25, p96))
        local v97 = false
        for v98 = 1, v_u_82:count() do
            if p_u_79._input:control_just_pressed(v_u_82:get(v98)) then
                v97 = true
                break;
            end;
        end;
        if v97 == false and (v_u_7:is_mobile() and p_u_79._input:control_just_pressed(v_u_8.KEY_CLICK)) then
            v97 = f_mobile_any_key_pressed()
        end;
        if v97 then
            p95:set_display_alpha(0.75)
            if v_u_84:count() + 1 <= v_u_83:count() then
                local v99 = v_u_83:get(v_u_84:count() + 1)
                if p_u_79._input:control_just_pressed(v99) or v_u_7:is_mobile() and f_mobile_key_pressed(v99) then
                    v_u_84:push_back(v99)
                    if v_u_84:count() == v_u_83:count() then
                        p95:set_disabled()
                        local v_u_100 = p_u_79._menus:push_menu(v_u_22:new(p_u_79, p_u_79._spui, p_u_79._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_79._evt:wait_on_event_once(v_u_11.EVT_SpecialEvent_RBBattle_Stage1_Server, function(p101, _) --[[ Line: 584 ]]
                            --[[ Upvalues: (ref 1): p_u_79, (copy 2): v_u_100, (ref 3): v_u_22, (ref 4): v_u_12, (ref 5): v_u_35 ]]
                            if p101 == true then
                                p_u_79._player_blob_manager:do_sync(function(_) --[[ Line: 589 ]]
                                    --[[ Upvalues: (ref 1): p_u_79, (ref 2): v_u_100, (ref 3): v_u_22, (ref 4): v_u_12, (ref 5): v_u_35 ]]
                                    p_u_79._menus:remove_menu(v_u_100)
                                    p_u_79._menus:push_menu(v_u_22:new(p_u_79, p_u_79._spui, p_u_79._menus):set_text("Secret Dance Acquired!", string.format("Got a new dance: \"%s\"!\nNow what could this be used for...?", v_u_12:singleton():get_dance_name_for_id(v_u_35:get_rbbattle_special_stage1_danceid()))))
                                end)
                            else
                                p_u_79._menus:remove_menu(v_u_100)
                            end;
                        end)
                        p_u_79._evt:fire_event_to_server(v_u_11.EVT_SpecialEvent_RBBattle_Stage1_Client)
                        return;
                    end;
                else
                    v_u_84:clear()
                end;
            end;
        end;
    end;
    v81:cons()
    return v81;
end;
return v_u_35;
