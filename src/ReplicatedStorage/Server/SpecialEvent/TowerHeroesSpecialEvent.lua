-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.Override)
local s_BadgeService_0 = game:GetService("BadgeService")
local v7 = {}
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
v8:require_server(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_9 ]]
    v_u_9 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v7.new = function(_, p_u_10) --[[ Name: new ]] --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_5, (copy 5): s_BadgeService_0, (copy 6): v_u_2, (copy 7): v_u_6, (copy 8): v_u_3 ]]
    local v11 = v_u_9.EventBase:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): s_BadgeService_0, (ref 6): v_u_2 ]]
        p_u_10._evt:wait_on_event(v_u_4.EVT_SpecialEvent_TowerHeroesClaimMini1_Client, function(p_u_12) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): s_BadgeService_0, (ref 6): v_u_2 ]]
            local function f_response(p13, p14) --[[ Name: response ]] --[[ Line: 25 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): p_u_12 ]]
                p_u_10._evt:fire_event_to_client(v_u_4.EVT_SpecialEvent_TowerHeroesClaimMini1_Server, p_u_12, p13, p14)
            end;
            if v_u_1:is_tower_heroes_event_active(p_u_10._api:get_day_event_list()) ~= true then
                return f_response(false, "Event is not active");
            end;
            p_u_10._player_blob_manager:get_verified_cached_blob(p_u_12.UserId, function(p15) --[[ Line: 29 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_response, (ref 3): v_u_5, (ref 4): s_BadgeService_0, (copy 5): p_u_12, (ref 6): v_u_2, (ref 7): p_u_10 ]]
                if v_u_1:tower_heroes_playerblob_get_claim_song_count(p15) < v_u_1:tower_heroes_get_claim_song_set():count() then
                    return f_response(false, string.format("You must get all %d \'RoBeats x Tower Heroes Event\' Normal mode songs to claim this Mini. Owned: %d", v_u_1:tower_heroes_get_claim_song_set():count(), v_u_1:tower_heroes_playerblob_get_claim_song_count(p15)));
                end;
                local v16 = v_u_1:get_pet1_id()
                local v17, v18 = v_u_5:playerblob_can_add_pet_of_petid(p15, v16)
                if v17 ~= true then
                    return f_response(false, v18);
                end;
                spawn(function() --[[ Line: 42 ]]
                    --[[ Upvalues: (ref 1): s_BadgeService_0, (ref 2): p_u_12, (ref 3): v_u_2 ]]
                    s_BadgeService_0:AwardBadge(p_u_12.UserId, 2124575373)
                    v_u_2:puts("EVT_SpecialEvent_TowerHeroesClaimMini1_Client awarded badge")
                end)
                v_u_5:server_grant_and_opt_equip_petid(p_u_10, p_u_12, v16, function(p19) --[[ Line: 46 ]]
                    --[[ Upvalues: (ref 1): f_response ]]
                    return f_response(true, p19.Message);
                end)
            end)
        end)
        p_u_10._evt:wait_on_event(v_u_4.EVT_SpecialEvent_TowerHeroesClaimMini2_Client, function(p_u_20) --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): s_BadgeService_0, (ref 4): v_u_1, (ref 5): v_u_5 ]]
            local function f_response(p21, p22) --[[ Name: response ]] --[[ Line: 53 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): p_u_20 ]]
                p_u_10._evt:fire_event_to_client(v_u_4.EVT_SpecialEvent_TowerHeroesClaimMini2_Server, p_u_20, p21, p22)
            end;
            spawn(function() --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): s_BadgeService_0, (copy 2): p_u_20, (ref 3): p_u_10, (copy 4): f_response, (ref 5): v_u_1, (ref 6): v_u_5 ]]
                local v_u_23 = s_BadgeService_0:UserHasBadgeAsync(p_u_20.UserId, 2124935159)
                p_u_10._post_fn:enqueue_function(function() --[[ Line: 58 ]]
                    --[[ Upvalues: (copy 1): v_u_23, (ref 2): f_response, (ref 3): p_u_10, (ref 4): p_u_20, (ref 5): v_u_1, (ref 6): v_u_5 ]]
                    if v_u_23 ~= true then
                        return f_response(false, "You must get a badge from Tower Heroes in order to claim this Mini. Beat the stage \'Idol Encore\' on Challenge Mode [Easy] Tower Heroes to do so!");
                    end;
                    p_u_10._player_blob_manager:get_verified_cached_blob(p_u_20.UserId, function(p24) --[[ Line: 60 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (ref 2): f_response, (ref 3): v_u_5, (ref 4): p_u_10, (ref 5): p_u_20 ]]
                        if v_u_1:tower_heroes_playerblob_get_claim_song_count(p24) < v_u_1:tower_heroes_get_claim_song_set():count() then
                            return f_response(false, string.format("You must get all %d \'RoBeats x Tower Heroes Event\' Normal mode songs to claim this Mini. Owned: %d", v_u_1:tower_heroes_get_claim_song_set():count(), v_u_1:tower_heroes_playerblob_get_claim_song_count(p24)));
                        end;
                        local v25 = v_u_1:get_pet2_id()
                        local v26, v27 = v_u_5:playerblob_can_add_pet_of_petid(p24, v25)
                        if v26 ~= true then
                            return f_response(false, v27);
                        end;
                        v_u_5:server_grant_and_opt_equip_petid(p_u_10, p_u_20, v25, function(p28) --[[ Line: 73 ]]
                            --[[ Upvalues: (ref 1): f_response ]]
                            return f_response(true, p28.Message);
                        end)
                    end)
                end)
            end)
        end)
    end;
    v_u_6:get_base_fn(v11, "can_playerid_start_songkey")
    v11.can_playerid_start_songkey = function(_, _, p29, p30) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 83 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        if p30 == v_u_1.EventMission.TowerHeroesEvent then
            return v_u_1:tower_heroes_get_playable_song_set():contains(p29);
        else
            return false;
        end;
    end;
    v_u_6:get_base_fn(v11, "write_special_event_data_for_play")
    v11.write_special_event_data_for_play = function(_, _, p31, _, _, p32, p33, p34) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_10, (ref 3): v_u_3 ]]
        if p32._event_info == v_u_1.EventMission.TowerHeroesEvent then
            local v35 = p_u_10._player_blob_manager:get_cached_blob(p32._id)
            if v35 ~= nil then
                if v_u_1:is_tower_heroes_event_active(p_u_10._api:get_day_event_list()) and v_u_1:tower_heroes_get_playable_song_set():contains(p31) then
                    local v36, v_u_37 = v_u_1:tower_heroes_get_songkey_grant_target_songkey(p31)
                    if v36 and v_u_3:get_song_key_owned_count(v35, v_u_37) == 0 then
                        p33:push_back(function(p38) --[[ Line: 100 ]]
                            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_37 ]]
                            v_u_3:add_song(p38, v_u_37)
                        end)
                        p34.ShowSongAcquiredPopup = true
                        p34.AcquiredSongKey = v_u_37
                    end;
                end;
            end;
        else
            return;
        end;
    end;
    f_cons()
    return v11;
end;
return v7;
