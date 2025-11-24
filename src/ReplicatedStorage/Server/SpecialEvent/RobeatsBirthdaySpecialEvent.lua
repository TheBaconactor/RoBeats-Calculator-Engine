-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.SongLaunchEventInfo)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.Override)
local v_u_5 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_6 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_7 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_8 = require(game.ReplicatedStorage.Pets.PetUtils)
local v9 = {}
local v10 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_11 = nil
v10:require_server(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    v_u_11 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v9.new = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_7, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_8, (copy 8): v_u_4, (copy 9): v_u_2 ]]
    local v13 = v_u_11.EventBase:new()
    local function _() --[[ Name: cons ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_3, (ref 3): v_u_1, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_5, (ref 7): v_u_8 ]]
        p_u_12._evt:wait_on_event(v_u_3.EVT_SpecialEvent_RobeatsBirthdayEventClaim_Client, function(p_u_14) --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_3, (ref 3): v_u_1, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_5, (ref 7): v_u_8 ]]
            local function f_response(p15, p16) --[[ Name: response ]] --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_3, (copy 3): p_u_14 ]]
                p_u_12._evt:fire_event_to_client(v_u_3.EVT_SpecialEvent_RobeatsBirthdayEventClaim_Server, p_u_14, p15, p16)
            end;
            if v_u_1:is_birthday_event_active(p_u_12._api:get_day_event_list()) ~= true then
                return f_response(false, "Event is not active");
            end;
            p_u_12._player_blob_manager:get_verified_cached_blob(p_u_14.UserId, function(p17) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_response, (ref 3): v_u_7, (ref 4): v_u_6, (ref 5): v_u_5, (ref 6): v_u_8, (ref 7): p_u_12, (copy 8): p_u_14 ]]
                if v_u_1:test_playerblob_can_claim_song_launch_claimed_id(p17, v_u_1:get_birthday_event_song_launch_claimed_id()) ~= true then
                    return f_response(false, "Already claimed.");
                end;
                v_u_1:playerblob_claim_song_launch_claimed_id(p17, v_u_1:get_birthday_event_song_launch_claimed_id())
                local v18 = v_u_1:get_birthday_event_fever_icon_material()
                local v19 = v_u_7:singleton():get_material(v18)
                v_u_6:add_crafting_materials_of_id(p17, v18, 1)
                if v19 and v19:is_fever_icon() then
                    p17.FeverIcon = v19:get_fever_icon_id()
                end;
                local v20 = v_u_1:get_birthday_event_dance_id()
                v_u_5:add_owned_danceid(p17, v20)
                v_u_5:set_danceid_equipped(p17, v20, true)
                v_u_5:validate_playerblob(p17)
                v_u_8:server_grant_and_opt_equip_petid(p_u_12, p_u_14, v_u_1:get_birthday_event_pet_id(), function(_) --[[ Line: 60 ]]
                    --[[ Upvalues: (ref 1): f_response ]]
                    return f_response(true, "RoBeats 5th Anniversary - Thanks for playing! Got:\n-Mini Alien Icon\n-\"Fever Time\" Dance\n-Birthday Alien Mini");
                end)
            end)
        end)
    end;
    v_u_4:get_base_fn(v13, "can_playerid_start_songkey")
    v13.can_playerid_start_songkey = function(_, _, p21, p22) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        if p22 == v_u_1.EventMission.RobeatsBirthdayEvent then
            return v_u_1:get_birthday_event_playable_song_set():contains(p21);
        else
            return false;
        end;
    end;
    v_u_4:get_base_fn(v13, "write_special_event_data_for_play")
    v13.write_special_event_data_for_play = function(_, _, p_u_23, _, _, p24, p25, p26) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_12, (ref 3): v_u_2 ]]
        if p24._event_info == v_u_1.EventMission.RobeatsBirthdayEvent then
            local v27 = p_u_12._player_blob_manager:get_cached_blob(p24._id)
            if v27 ~= nil then
                if v_u_1:is_birthday_event_active(p_u_12._api:get_day_event_list()) and (v_u_1:get_birthday_event_playable_song_set():contains(p_u_23) and v_u_2:get_song_key_owned_count(v27, p_u_23) == 0) then
                    p25:push_back(function(p28) --[[ Line: 83 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_23 ]]
                        v_u_2:add_song(p28, p_u_23)
                    end)
                    p26.ShowSongAcquiredPopup = true
                    p26.AcquiredSongKey = p_u_23
                end;
            end;
        else
            return;
        end;
    end;
    p_u_12._evt:wait_on_event(v_u_3.EVT_SpecialEvent_RobeatsBirthdayEventClaim_Client, function(p_u_29) --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_3, (ref 3): v_u_1, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_5, (ref 7): v_u_8 ]]
        local function f_response(p30, p31) --[[ Name: response ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_3, (copy 3): p_u_29 ]]
            p_u_12._evt:fire_event_to_client(v_u_3.EVT_SpecialEvent_RobeatsBirthdayEventClaim_Server, p_u_29, p30, p31)
        end;
        if v_u_1:is_birthday_event_active(p_u_12._api:get_day_event_list()) ~= true then
            return f_response(false, "Event is not active");
        end;
        p_u_12._player_blob_manager:get_verified_cached_blob(p_u_29.UserId, function(p32) --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_response, (ref 3): v_u_7, (ref 4): v_u_6, (ref 5): v_u_5, (ref 6): v_u_8, (ref 7): p_u_12, (copy 8): p_u_29 ]]
            if v_u_1:test_playerblob_can_claim_song_launch_claimed_id(p32, v_u_1:get_birthday_event_song_launch_claimed_id()) ~= true then
                return f_response(false, "Already claimed.");
            end;
            v_u_1:playerblob_claim_song_launch_claimed_id(p32, v_u_1:get_birthday_event_song_launch_claimed_id())
            local v33 = v_u_1:get_birthday_event_fever_icon_material()
            local v34 = v_u_7:singleton():get_material(v33)
            v_u_6:add_crafting_materials_of_id(p32, v33, 1)
            if v34 and v34:is_fever_icon() then
                p32.FeverIcon = v34:get_fever_icon_id()
            end;
            local v35 = v_u_1:get_birthday_event_dance_id()
            v_u_5:add_owned_danceid(p32, v35)
            v_u_5:set_danceid_equipped(p32, v35, true)
            v_u_5:validate_playerblob(p32)
            v_u_8:server_grant_and_opt_equip_petid(p_u_12, p_u_29, v_u_1:get_birthday_event_pet_id(), function(_) --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): f_response ]]
                return f_response(true, "RoBeats 5th Anniversary - Thanks for playing! Got:\n-Mini Alien Icon\n-\"Fever Time\" Dance\n-Birthday Alien Mini");
            end)
        end)
    end)
    return v13;
end;
return v9;
