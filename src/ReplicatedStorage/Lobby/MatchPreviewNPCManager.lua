-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Lobby.NPC.WebNPC)
require(game.ReplicatedStorage.Local.AnimationManager)
require(game.ReplicatedStorage.Shared.WebNPCAnchors)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_6 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_9 = require(game.ReplicatedStorage.Shared.PlayerStatus)
local v_u_10 = require(game.ReplicatedStorage.Lobby.NPC.MatchPreviewNPC)
return {
    ["new"] = function(_, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_8, (copy 4): v_u_9, (copy 5): v_u_7, (copy 6): v_u_1, (copy 7): v_u_5, (copy 8): v_u_3, (copy 9): v_u_6, (copy 10): v_u_10 ]]
        local v14 = {}
        local v_u_15 = v_u_2:new()
        local function _() end;
        local function f_status_should_make_npc(p16) --[[ Name: status_should_make_npc ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_12, (ref 3): v_u_8, (ref 4): v_u_9 ]]
            if v_u_4:should_hide_npcs(p_u_12) then
                return false;
            end;
            if v_u_8:get_mode() == v_u_8.Mode.None then
                return false;
            end;
            local v17 = p16:get_mode()
            return (v17 == v_u_9.Mode.MatchPlaying or v17 == v_u_9.Mode.MatchFinished) and true or v17 == v_u_9.Mode.InSettings;
        end;
        local l_MatchPreviewNPC_0 = v_u_7.Test.MatchPreviewNPC
        v14.update = function(p18, _) --[[ Name: update ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): l_MatchPreviewNPC_0, (copy 3): p_u_12, (ref 4): v_u_1, (copy 5): f_status_should_make_npc, (copy 6): v_u_15, (ref 7): v_u_8, (ref 8): v_u_2, (copy 9): p_u_13, (ref 10): v_u_5, (ref 11): v_u_3, (ref 12): v_u_6 ]]
            local v19 = v_u_7:singleton()
            if v19:should_run(l_MatchPreviewNPC_0) == false then
                return;
            end;
            local v20 = v19:get_test_state(l_MatchPreviewNPC_0)
            v20:get_dt_scale()
            p_u_12._input:set_frame_index_state(v20)
            v_u_1:profilebegin("MatchPreviewNPCManager:update")
            local v21 = 1
            for v22, v23 in p_u_12._player_status_manager:get_id_to_playerstatus_dict():key_itr() do
                v_u_1:profilebegin("MatchPreviewNPCManager:update id_to_playerstatus_dict key_itr")
                v21 = v21 + 1
                if v21 > 120 then
                    break;
                end;
                local v24 = f_status_should_make_npc(v23)
                if v22 == v_u_1:get_local_userid() or (v_u_15:contains(v22) == true or v24 ~= true) then
                    if v_u_15:contains(v22) == true and v24 ~= true then
                        v_u_1:profilebegin("MatchPreviewNPCManager:remove_npc1")
                        p18:remove_npc(v22)
                        v_u_1:profileend()
                    end;
                elseif v_u_8:character_of_distance_and_priority_would_be_visible((v_u_1:get_localplayer_cframe().Position - v23:get_cframe().Position).magnitude) == true then
                    v_u_1:profilebegin("MatchPreviewNPCManager:create_npc")
                    p18:create_npc(v22)
                    v_u_1:profileend()
                end;
                v_u_1:profileend()
            end;
            v_u_2:remove_if(v_u_15, function(_, p25) --[[ Line: 77 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_12, (ref 3): p_u_13, (ref 4): v_u_15 ]]
                v_u_1:profilebegin("MatchPreviewNPCManager:update _id_to_match_preview_npc:remove_if")
                local v26 = p_u_12._player_status_manager:contains_status_for_id(p25) ~= true
                if v26 then
                    v_u_1:profilebegin("MatchPreviewNPCManager:remove_npc2")
                    p_u_13:remove_npc(v_u_15:get(p25))
                    v_u_1:profileend()
                end;
                v_u_1:profileend()
                return v26;
            end)
            v_u_1:profileend()
            if v_u_1:is_dev_build() and (p_u_12._input:control_just_pressed(v_u_5.KEY_DEBUG_4) and p_u_12._menus:top_menu_swallows_input() == false) then
                local v27 = string.format("MatchPreviewNPCManager_debug id_to_playerstatus_dict(%d) _id_to_match_preview_npc(%d) npc_count(%d) web_npc(%d)", p_u_12._player_status_manager:get_id_to_playerstatus_dict():count(), v_u_15:count(), p_u_13:get_id_to_npcs():count(), p_u_13:get_web_npc_manager():count())
                v_u_3:puts(v27)
                p_u_12._chat:get_system_channel():add_message_to_channel(v_u_6:new(v27))
            end;
            p_u_12._input:set_frame_index_state(nil)
        end;
        v14.create_npc = function(_, p_u_28) --[[ Name: create_npc ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_11, (copy 3): p_u_12, (copy 4): p_u_13, (copy 5): v_u_15, (ref 6): v_u_8, (ref 7): v_u_3 ]]
            local v30, v31 = pcall(function() --[[ Line: 108 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_11, (ref 3): p_u_12, (copy 4): p_u_28, (ref 5): p_u_13, (ref 6): v_u_15, (ref 7): v_u_8 ]]
                local v29 = v_u_10:new(p_u_11, p_u_12, p_u_12._player_status_manager:get_status_for_id(p_u_28))
                p_u_13:add_npc(v29)
                v_u_15:add(p_u_28, v29)
                v_u_8:do_post_update()
            end)
            if v30 ~= true then
                v_u_3:warnf("MatchPreviewNPCManager:create_npc failed: %s", v31)
            end;
        end;
        v14.remove_npc = function(_, p32) --[[ Name: remove_npc ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): p_u_13, (copy 2): v_u_15 ]]
            p_u_13:remove_npc(v_u_15:get(p32))
            v_u_15:remove(p32)
        end;
        v14.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 124 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            v_u_15:clear()
        end;
        return v14;
    end
};
