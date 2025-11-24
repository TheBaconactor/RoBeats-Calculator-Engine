-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Lobby.PlayerNametag)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.CharacterCloneCache)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
return {
    ["new"] = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_9, (copy 4): v_u_2, (copy 5): v_u_5, (copy 6): v_u_1, (copy 7): v_u_7, (copy 8): v_u_10, (copy 9): v_u_11, (copy 10): v_u_6, (copy 11): v_u_8 ]]
        local v_u_13 = {}
        local v_u_14 = v_u_3:new()
        local v_u_15 = v_u_3:new()
        local v_u_16 = v_u_4:new()
        v_u_13.get_id_to_nametag_count = function(_) --[[ Name: get_id_to_nametag_count ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            return v_u_14:count();
        end;
        v_u_13.get_id_to_playerinfo_count = function(_) --[[ Name: get_id_to_playerinfo_count ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            return v_u_15:count();
        end;
        v_u_13.get_id_to_playerinfo = function(_) --[[ Name: get_id_to_playerinfo ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            return v_u_15;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_12, (ref 3): v_u_2, (copy 4): v_u_15, (copy 5): v_u_13, (ref 6): v_u_5, (ref 7): v_u_1, (ref 8): v_u_7, (ref 9): v_u_10, (ref 10): v_u_11, (copy 11): v_u_14 ]]
            v_u_9:set_local_services(p_u_12)
            p_u_12._evt:wait_on_event(v_u_2.EVT_Lobby_ServerNotifyAllPlayerEnteredLobby, function(p17, p18, p_u_19) --[[ Line: 30 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_13, (ref 3): v_u_5 ]]
                v_u_15:add(p17, p18)
                v_u_13:player_create_nametag(p17)
                v_u_5:ptry(function() --[[ Line: 33 ]]
                    --[[ Upvalues: (copy 1): p_u_19 ]]
                    p_u_19.Humanoid:SetStateEnabled(Enum.HumanoidStateType.FallingDown, false)
                    p_u_19.Humanoid:SetStateEnabled(Enum.HumanoidStateType.Ragdoll, false)
                end)
            end)
            p_u_12._evt:wait_on_event(v_u_2.EVT_Lobby_ServerResponseRequestPlayerInfoList, function(p20) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_15 ]]
                for v21 = 1, #p20 do
                    local v22 = p20[v21]
                    if v22 and v22.UserId ~= nil then
                        v_u_15:add(v22.UserId, v22)
                    end;
                end;
            end)
            p_u_12._evt:wait_on_event(v_u_2.EVT_Lobby_ServerPushPlayerInfoUpdated, function(p23, p24) --[[ Line: 46 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_15 ]]
                v_u_13:clear_info_for_playerid(p23)
                v_u_15:add(p23, p24)
            end)
            p_u_12._evt:wait_on_event(v_u_2.EVT_Lobby_ServerNotifySyncDanceToPlayer, function(p25, p26) --[[ Line: 50 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_7 ]]
                if p25 ~= v_u_5:get_local_userid() then
                    local v27 = nil
                    local v28 = nil
                    for _, v29 in pairs(game.Players:GetPlayers()) do
                        if v29.UserId == p25 then
                            v27 = v29
                        end;
                        if v29.UserId == p26 then
                            v28 = v29
                        end;
                    end;
                    if v27 == nil or v28 == nil then
                        return v_u_1:warnf("EVT_Lobby_ServerNotifySyncDanceToPlayer sync_player(%s) target_player(%s)", tostring(v27), (tostring(v28)));
                    end;
                    local v_u_30 = v_u_5:get_player_animator(v27)
                    local v_u_31 = v_u_5:get_player_animator(v28)
                    spawn(function() --[[ Line: 65 ]]
                        --[[ Upvalues: (copy 1): v_u_30, (copy 2): v_u_31, (ref 3): v_u_1, (ref 4): v_u_7 ]]
                        wait(0.1)
                        for _ = 1, 3 do
                            if v_u_30 == nil or v_u_31 == nil then
                                return v_u_1:warnf("EVT_Lobby_ServerNotifySyncDanceToPlayer animator is nil");
                            end;
                            for _, v32 in pairs(v_u_31:GetPlayingAnimationTracks()) do
                                for _, v33 in pairs(v_u_30:GetPlayingAnimationTracks()) do
                                    if v32.Animation and (v33.Animation and (v32.Animation.AnimationId == v33.Animation.AnimationId and v_u_7:singleton():assetid_is_dance(v33.Animation.AnimationId))) then
                                        v33.TimePosition = v32.TimePosition
                                    end;
                                end;
                            end;
                            wait(0.2)
                        end;
                    end)
                end;
            end)
            v_u_5:ptry(function() --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_11, (ref 5): p_u_12 ]]
                v_u_10:get_events_folder().LobbyCharacterStoredDoCleanup.OnClientEvent:connect(function(p34, p35, p36) --[[ Line: 87 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_11 ]]
                    local v37 = v_u_10:get_character_model_for_playerid(v_u_5:get_local_userid())
                    if v37 == nil then
                        return v_u_1:warnf("LobbyCharacterStoredDoCleanup source_character_model is nil");
                    end;
                    if v_u_5:is_dev_build() then
                        v_u_1:puts("LobbyCharacterStoredDoCleanup character(%s) _stored_lobby_character_folder(%s) target_userid(%s)", p34:GetFullName(), p35:GetFullName(), (tostring(p36)))
                    end;
                    if v_u_11:remove_managed_character(p34) ~= true and (v_u_5:is_dev_build() and p36 ~= v_u_5:get_local_userid()) then
                        v_u_1:warnf("LobbyCharacterStoredDoCleanup(%s) failed to remove CharacterCulling managed character", p34:GetFullName())
                    end;
                    v_u_5:remove_all_elements_of_model_not_present_in_source(p34, v37)
                    p34.Parent = p35
                    if v_u_5:is_dev_build() then
                        v_u_1:puts("LobbyCharacterStoredDoCleanup character(%s) _stored_lobby_character_folder(%s)", p34:GetFullName(), p35:GetFullName())
                    end;
                end)
                v_u_10:get_events_folder().LobbyPetNPCStoredDoCleanup.OnClientEvent:connect(function(p38, p39, p40) --[[ Line: 111 ]]
                    --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_11, (ref 3): v_u_5, (ref 4): v_u_1 ]]
                    if p_u_12 ~= nil and p_u_12._follow_npc_manager ~= nil then
                        if v_u_11:remove_managed_character(p38) ~= true and (v_u_5:is_dev_build() and p40 ~= v_u_5:get_local_userid()) then
                            v_u_1:warnf("LobbyPetNPCStoredDoCleanup(%s) failed to remove CharacterCulling managed character", p38:GetFullName())
                        end;
                        if p_u_12._follow_npc_manager:character_notify_cleanup(p38) ~= true and (v_u_5:is_dev_build() and p40 ~= v_u_5:get_local_userid()) then
                            v_u_1:warnf("LobbyPetNPCStoredDoCleanup(%s) failed to remove FollowNPCManager managed character", p38:GetFullName())
                        end;
                        v_u_5:remove_objects_not_present_in_source(p38)
                        p38.Parent = p39
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("LobbyPetNPCStoredDoCleanup character(%s) neu_parent_folder(%s)", p38:GetFullName(), p39:GetFullName())
                        end;
                    end;
                end)
            end)
            game.Players.PlayerRemoving:connect(function(p41) --[[ Line: 137 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_9 ]]
                if v_u_14:contains(p41.UserId) then
                    v_u_14:get(p41.UserId):set_remove()
                end;
                v_u_15:remove(p41.UserId)
                v_u_9:playerid_disconnecting(p41.UserId)
            end)
        end;
        v_u_13.create_nametags_for_existing_players = function(p42) --[[ Name: create_nametags_for_existing_players ]] --[[ Line: 147 ]]
            --[[ Upvalues: (copy 1): v_u_16 ]]
            for _, v43 in pairs(game.Players:GetPlayers()) do
                if v43.Character ~= nil then
                    p42:player_create_nametag(v43.UserId)
                    v_u_16:push_back(v43.UserId)
                end;
            end;
        end;
        v_u_13.player_create_nametag = function(p44, p45) --[[ Name: player_create_nametag ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_12, (copy 3): v_u_14, (copy 4): v_u_15, (copy 5): v_u_16 ]]
            local v46 = v_u_6:new(p_u_12, p44, p45)
            if v_u_14:contains(p45) then
                v_u_14:get(p45):do_remove()
                v_u_14:remove(p45)
            end;
            if v_u_15:contains(p45) ~= true then
                v_u_16:push_back(p45)
            end;
            v_u_14:add(p45, v46)
            return v46;
        end;
        v_u_13.get_player_info = function(_, p47) --[[ Name: get_player_info ]] --[[ Line: 172 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            if v_u_15:contains(p47) == false then
                return false, 0, 0, nil;
            end;
            local v48 = v_u_15:get(p47)
            return true, v48.MissionRank, v48.CurrentTitleID, v48;
        end;
        v_u_13.clear_info_for_playerid = function(_, p49) --[[ Name: clear_info_for_playerid ]] --[[ Line: 178 ]]
            --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_14 ]]
            v_u_15:remove(p49)
            if v_u_14:contains(p49) then
                v_u_14:get(p49):set_to_load_info()
            end;
        end;
        local v_u_50 = v_u_4:new()
        local l_CharacterManager_0 = v_u_8.Test.CharacterManager
        v_u_13.update = function(_, p51) --[[ Name: update ]] --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): v_u_16, (copy 2): p_u_12, (ref 3): v_u_2, (ref 4): v_u_8, (copy 5): l_CharacterManager_0, (copy 6): v_u_14, (ref 7): v_u_5, (copy 8): v_u_50 ]]
            if v_u_16:count() > 0 then
                local v52 = {}
                for v53 = 1, v_u_16:count() do
                    v52[v53] = v_u_16:get(v53)
                end;
                p_u_12._evt:fire_event_to_server(v_u_2.EVT_Lobby_ClientRequestPlayerInfoList, v52)
                v_u_16:clear()
            end;
            local v54 = v_u_8:singleton()
            if v54:should_run(l_CharacterManager_0) == false then
                local v55 = v54:ui_needs_refresh()
                for _, v56 in v_u_14:key_itr() do
                    if v56:off_frame_index_check_root_part_position() or v55 then
                        v56:update(p51)
                    end;
                end;
            else
                local v57 = v54:get_test_state(l_CharacterManager_0)
                local v58 = v57:get_dt_scale()
                p_u_12._input:set_frame_index_state(v57)
                v_u_5:profilebegin("CharacterManager:update")
                for v59, v60 in v_u_14:key_itr() do
                    v60:update(v58)
                    if v60:should_remove() then
                        v_u_50:push_back(v59)
                    end;
                end;
                for v61 = 1, v_u_50:count() do
                    local v62 = v_u_50:get(v61)
                    if v_u_14:contains(v62) then
                        v_u_14:get(v62):do_remove()
                    end;
                    v_u_14:remove(v62)
                end;
                v_u_50:clear()
                v_u_5:profileend()
                p_u_12._input:set_frame_index_state(nil)
            end;
        end;
        v_u_13.print_debug_state = function(_) --[[ Name: print_debug_state ]] --[[ Line: 233 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_14 ]]
            v_u_1:warnf("CharacterManager _id_to_nametag_entry(%d)", v_u_14:count())
            for _, v63 in v_u_14:key_itr() do
                v63:print_debug_state()
            end;
        end;
        local v_u_64 = 1
        v_u_13.set_nametag_alpha_multiplier = function(_, p65) --[[ Name: set_nametag_alpha_multiplier ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_64 ]]
            v_u_64 = p65
        end;
        v_u_13.get_nametag_alpha_multiplier = function(_) --[[ Name: get_nametag_alpha_multiplier ]] --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): v_u_64 ]]
            return v_u_64;
        end;
        f_cons()
        return v_u_13;
    end
};
