-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Lobby.NPC.WebNPC)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.WebNPCAnchors)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v13 = {}
local v_u_24 = {
    ["new"] = function(_, p_u_14, p_u_15, p_u_16, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1, (copy 3): v_u_7, (copy 4): v_u_11, (copy 5): v_u_4 ]]
        local v20 = {}
        local l__webnpc_local_model_cache_0 = p_u_15._webnpc_local_model_cache
        v20.get_anchor_cframe = function(_) --[[ Name: get_anchor_cframe ]] --[[ Line: 33 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            return p_u_19;
        end;
        v20.create_npc = function(_) --[[ Name: create_npc ]] --[[ Line: 34 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_5, (copy 3): p_u_15, (copy 4): l__webnpc_local_model_cache_0, (copy 5): p_u_18, (copy 6): p_u_14, (ref 7): v_u_1, (copy 8): p_u_19, (ref 9): v_u_7, (ref 10): v_u_11, (ref 11): v_u_4, (copy 12): p_u_16 ]]
            p_u_17:flag_as_loading_npc(true)
            spawn(function() --[[ Line: 36 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_5, (ref 3): p_u_15, (ref 4): l__webnpc_local_model_cache_0, (ref 5): p_u_18, (ref 6): p_u_14, (ref 7): v_u_1, (ref 8): p_u_19, (ref 9): v_u_7, (ref 10): v_u_11, (ref 11): v_u_4, (ref 12): p_u_16 ]]
                if p_u_17:is_kill() == true or v_u_5:should_hide_npcs(p_u_15) then
                    p_u_17:flag_as_loading_npc(false)
                else
                    local v_u_21 = l__webnpc_local_model_cache_0:create_cached_character_model_for_playerid(p_u_18:get_userid(), p_u_14:get_character_group_id())
                    p_u_15._update_enqueue_fn:enqueue_function(function() --[[ Line: 45 ]]
                        --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_5, (ref 3): p_u_15, (ref 4): v_u_1, (copy 5): v_u_21, (ref 6): p_u_18, (ref 7): p_u_19, (ref 8): v_u_7, (ref 9): p_u_14, (ref 10): v_u_11, (ref 11): v_u_4, (ref 12): p_u_16 ]]
                        if p_u_17:is_kill() == true or v_u_5:should_hide_npcs(p_u_15) then
                            p_u_17:flag_as_loading_npc(false)
                        else
                            v_u_1:profilebegin("WebNPC:new")
                            v_u_21.Name = p_u_18:get_name()
                            v_u_21.Humanoid.RootPart.Anchored = true
                            v_u_21.Humanoid.RootPart.CFrame = p_u_19
                            v_u_21.Parent = v_u_5:get_npc_root()
                            local v22 = v_u_7:new(p_u_17, p_u_14, p_u_15, v_u_21, p_u_18)
                            local v23 = p_u_18:get_danceid()
                            if v_u_11:singleton():contains_dance_for_id(v23) ~= true then
                                v_u_4:warnf("WebNPCManager itr_npc_data danceid(%s) not found, setting random", (tostring(v23)))
                                v23 = v_u_11:singleton():get_default_owned_danceid_set():key_list():random()
                            end;
                            v22:set_animation_key(v_u_11:singleton():get_dance_assetid_for_id(v23))
                            p_u_16:add_npc(v22)
                            p_u_17:push_back_loaded_npc(v22)
                            p_u_17:flag_as_loading_npc(false)
                            v_u_1:profileend()
                        end;
                    end)
                end;
            end)
        end;
        return v20;
    end
}
v13.new = function(_, p_u_25, p_u_26, p_u_27) --[[ Name: new ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_9, (copy 5): v_u_4, (copy 6): v_u_1, (copy 7): v_u_10, (copy 8): v_u_8, (copy 9): v_u_24, (copy 10): v_u_12 ]]
    local v_u_28 = {}
    local v_u_29 = v_u_3:new()
    local v_u_30 = false
    v_u_28.is_kill = function(_) --[[ Name: is_kill ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    local v_u_31 = v_u_2:new()
    local v_u_32 = false
    v_u_28.flag_as_loading_npc = function(_, p33) --[[ Name: flag_as_loading_npc ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        v_u_32 = p33
    end;
    local v_u_34 = v_u_2:new()
    v_u_28.push_back_loaded_npc = function(_, p35) --[[ Name: push_back_loaded_npc ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): v_u_34 ]]
        v_u_34:push_back(p35)
    end;
    local function _() --[[ Name: cons ]] --[[ Line: 98 ]]
        --[[ Upvalues: (copy 1): p_u_26, (ref 2): v_u_6, (ref 3): v_u_9, (ref 4): v_u_4, (ref 5): v_u_1, (copy 6): v_u_29, (ref 7): v_u_3, (ref 8): v_u_2, (ref 9): v_u_10, (ref 10): v_u_8, (copy 11): v_u_31, (ref 12): v_u_24, (copy 13): p_u_25, (copy 14): p_u_27, (copy 15): v_u_28 ]]
        p_u_26._evt:wait_on_event_once(v_u_6.EVT_WebNPC_ServerInfoResponse, function(p36) --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_4, (ref 3): v_u_1, (ref 4): v_u_29, (ref 5): p_u_26, (ref 6): v_u_3, (ref 7): v_u_2, (ref 8): v_u_10, (ref 9): v_u_8, (ref 10): v_u_31, (ref 11): v_u_24, (ref 12): p_u_25, (ref 13): p_u_27, (ref 14): v_u_28 ]]
            if v_u_9.LogWebNPCData == true then
                v_u_4:warnf("WebNPCData(%s)", v_u_1:table_to_string(p36))
            end;
            for v37, v38 in pairs(p36.VisitedList) do
                v_u_29:add(tonumber(v37), v38)
            end;
            local l_WebNPCInfo_0 = p36.WebNPCInfo
            local l__webnpc_local_model_cache_1 = p_u_26._webnpc_local_model_cache
            l__webnpc_local_model_cache_1:mark_for_delete_all_cached_models()
            local v39 = v_u_3:new()
            local v40 = v_u_2:new()
            for v41 = 1, #l_WebNPCInfo_0 do
                local v42 = v_u_10.NPCData:from_table(l_WebNPCInfo_0[v41])
                l__webnpc_local_model_cache_1:unmark_for_delete_playerid(v42:get_userid())
                local v43 = v_u_8:get_cframe_for_anchor_name(v42:get_anchor())
                if v43 then
                    v_u_31:push_back(v_u_24:new(p_u_25, p_u_26, p_u_27, v_u_28, v42, v43))
                else
                    v_u_4:warnf("webnpc_anchor not found(%s)", v42:get_anchor())
                end;
                v39:add(v42:get_tier(), (v39:get(v42:get_tier()) or 0) + 1)
                v40:push_back(v42:get_webnpcid())
            end;
            l__webnpc_local_model_cache_1:clear_all_marked_for_delete_models()
        end)
        p_u_26._evt:fire_event_to_server(v_u_6.EVT_WebNPC_ClientRequestInfo)
    end;
    v_u_28.webnpcid_should_trigger_reward = function(_, p44) --[[ Name: webnpcid_should_trigger_reward ]] --[[ Line: 147 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        local v45 = v_u_29:contains(p44)
        if v45 then
            v45 = v_u_29:get(p44) == false
        end;
        return v45;
    end;
    v_u_28.trigger_reward_local_cache = function(_, p46) --[[ Name: trigger_reward_local_cache ]] --[[ Line: 151 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        v_u_29:add(p46, true)
    end;
    v_u_28.update = function(_, _) --[[ Name: update ]] --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_12, (ref 3): v_u_32, (copy 4): v_u_31 ]]
        v_u_1:profilebegin("WebNPCManager:update")
        if v_u_12:get_mode() ~= v_u_12.Mode.None == true and (v_u_32 ~= true and v_u_31:count() > 0) then
            local l_Position_0 = v_u_1:get_localplayer_cframe().Position
            for v47 = v_u_31:count(), 1, -1 do
                local v48 = v_u_31:get(v47)
                if v_u_12:character_of_distance_and_priority_would_be_visible((l_Position_0 - v48:get_anchor_cframe().Position).magnitude) == true then
                    v48:create_npc()
                    v_u_31:remove_at(v47)
                    break;
                end;
            end;
        end;
        v_u_1:profileend()
    end;
    v_u_28.count = function(_) --[[ Name: count ]] --[[ Line: 177 ]]
        --[[ Upvalues: (copy 1): v_u_34 ]]
        return v_u_34:count();
    end;
    v_u_28.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_30, (copy 2): v_u_31 ]]
        v_u_30 = true
        v_u_31:clear()
    end;
    p_u_26._evt:wait_on_event_once(v_u_6.EVT_WebNPC_ServerInfoResponse, function(p49) --[[ Line: 99 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_4, (ref 3): v_u_1, (copy 4): v_u_29, (copy 5): p_u_26, (ref 6): v_u_3, (ref 7): v_u_2, (ref 8): v_u_10, (ref 9): v_u_8, (copy 10): v_u_31, (ref 11): v_u_24, (copy 12): p_u_25, (copy 13): p_u_27, (copy 14): v_u_28 ]]
        if v_u_9.LogWebNPCData == true then
            v_u_4:warnf("WebNPCData(%s)", v_u_1:table_to_string(p49))
        end;
        for v50, v51 in pairs(p49.VisitedList) do
            v_u_29:add(tonumber(v50), v51)
        end;
        local l_WebNPCInfo_1 = p49.WebNPCInfo
        local l__webnpc_local_model_cache_2 = p_u_26._webnpc_local_model_cache
        l__webnpc_local_model_cache_2:mark_for_delete_all_cached_models()
        local v52 = v_u_3:new()
        local v53 = v_u_2:new()
        for v54 = 1, #l_WebNPCInfo_1 do
            local v55 = v_u_10.NPCData:from_table(l_WebNPCInfo_1[v54])
            l__webnpc_local_model_cache_2:unmark_for_delete_playerid(v55:get_userid())
            local v56 = v_u_8:get_cframe_for_anchor_name(v55:get_anchor())
            if v56 then
                v_u_31:push_back(v_u_24:new(p_u_25, p_u_26, p_u_27, v_u_28, v55, v56))
            else
                v_u_4:warnf("webnpc_anchor not found(%s)", v55:get_anchor())
            end;
            v52:add(v55:get_tier(), (v52:get(v55:get_tier()) or 0) + 1)
            v53:push_back(v55:get_webnpcid())
        end;
        l__webnpc_local_model_cache_2:clear_all_marked_for_delete_models()
    end)
    p_u_26._evt:fire_event_to_server(v_u_6.EVT_WebNPC_ClientRequestInfo)
    return v_u_28;
end;
return v13;
