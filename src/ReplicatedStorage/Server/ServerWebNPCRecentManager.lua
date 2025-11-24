-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
local v_u_6 = require(game.ReplicatedStorage.Shared.CooldownDelay)
require(game.ReplicatedStorage.Shared.AssertType)
local v7 = {}
local v_u_8 = v_u_4:is_dev_build() and 5 or 20
v7.new = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (ref 3): v_u_8, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_1 ]]
    local v10 = {
        ["player_disconnecting"] = function(_, _) end
    }
    local v_u_11 = v_u_2:new()
    local v_u_12 = v_u_6:new()
    local function f_get_playerid_recent_web_npcs_list(p_u_13, p_u_14) --[[ Name: get_playerid_recent_web_npcs_list ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): p_u_9 ]]
        if v_u_11:contains(p_u_13) then
            return p_u_14(v_u_11:get(p_u_13));
        end;
        p_u_9._datastore_api:get_playerid_recent_web_npcs_list(p_u_13, function(p15) --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_13, (copy 3): p_u_14 ]]
            v_u_11:add(p_u_13, p15)
            p_u_14(p15)
        end)
    end;
    local function _(p16) --[[ Name: queue_playerid_webnpc_recent_list_datastore_sync ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_12, (ref 2): v_u_8 ]]
        v_u_12:add_cooldown_to_id(p16, v_u_8)
    end;
    v10.start = function(_) --[[ Name: start ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_3, (copy 3): f_get_playerid_recent_web_npcs_list, (ref 4): v_u_5 ]]
        p_u_9._evt:wait_on_event(v_u_3.EVT_WebNPC_ClientRequestRecent, function(p_u_17, _) --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): f_get_playerid_recent_web_npcs_list, (ref 2): p_u_9, (ref 3): v_u_3, (ref 4): v_u_5 ]]
            f_get_playerid_recent_web_npcs_list(p_u_17.UserId, function(p18) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_3, (copy 3): p_u_17, (ref 4): v_u_5 ]]
                p_u_9._evt:fire_event_to_client(v_u_3.EVT_WebNPC_ServerResponseRecent, p_u_17, v_u_5.NPCData:list_to_table(p18))
            end)
        end)
    end;
    v10.update = function(_, p19) --[[ Name: update ]] --[[ Line: 48 ]]
        --[[ Upvalues: (copy 1): v_u_12, (ref 2): v_u_4, (copy 3): v_u_11, (copy 4): p_u_9, (ref 5): v_u_2 ]]
        v_u_12:update(p19)
        if v_u_12:get_frame_removed_ids():count() > 0 then
            v_u_4:ptry(function() --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (ref 3): p_u_9 ]]
                for _, v20 in v_u_12:get_frame_removed_ids():key_itr() do
                    if v_u_11:contains(v20) then
                        p_u_9._datastore_api:write_playerid_recent_web_npcs_list(v20, v_u_11:get(v20))
                    end;
                end;
            end)
        end;
        v_u_2:remove_if(v_u_11, function(_, p21) --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_12 ]]
            return p_u_9._player_manager:id_to_player(p21) == nil and v_u_12:is_on_cooldown(p21) ~= true;
        end)
    end;
    v10.flag_playerid_webnpcid_as_recent = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: flag_playerid_webnpcid_as_recent ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): f_get_playerid_recent_web_npcs_list, (ref 2): v_u_1, (copy 3): v_u_12, (ref 4): v_u_8 ]]
        f_get_playerid_recent_web_npcs_list(p_u_22, function(p25) --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_23, (ref 3): p_u_24, (copy 4): p_u_22, (ref 5): v_u_12, (ref 6): v_u_8 ]]
            local l_END_0 = v_u_1.END
            v_u_1:for_each(p25, function(p26, p27) --[[ Line: 75 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): l_END_0 ]]
                if p26:get_webnpcid() ~= p_u_23 then
                    return true;
                end;
                l_END_0 = p27
                return false;
            end)
            if l_END_0 == v_u_1.END then
                if p_u_24 ~= nil then
                    p25:push_front(p_u_24)
                    if p25:count() > 100 then
                        p25:pop_back()
                    end;
                end;
            else
                p_u_24 = p25:get(l_END_0)
                p25:remove_at(l_END_0)
                if p_u_24 ~= nil then
                    p25:push_front(p_u_24)
                end;
            end;
            v_u_12:add_cooldown_to_id(p_u_22, v_u_8)
        end)
    end;
    return v10;
end;
return v7;
