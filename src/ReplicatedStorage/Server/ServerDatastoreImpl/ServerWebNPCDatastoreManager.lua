-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Time elapsed: 21 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Shared.APICooldown)
require(game.ReplicatedStorage.Server.ServerDatastoreImpl.LeaderboardDSParticipation)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local s_DataStoreService_0 = game:GetService("DataStoreService")
local v11 = {}
local v_u_27 = {
    ["new"] = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_8 ]]
        local v14 = {
            ["get_key"] = function(p13) --[[ Name: get_key ]] --[[ Line: 71 ]]
                if p13:has_web_npc_id() then
                    return string.format("webnpcid_%d", p13:get_web_npc_id());
                else
                    return not p13:has_tier_and_index() and "invalid" or string.format("tier_%d_index_%d", p13:get_tier(), p13:get_index());
                end;
            end
        }
        v14.get_queue_time = function(_) --[[ Name: get_queue_time ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            return p_u_12;
        end;
        local v_u_15 = false
        local v_u_16 = 0
        v14.set_web_npc_id = function(p17, p18) --[[ Name: set_web_npc_id ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_16, (ref 3): v_u_15 ]]
            v_u_6:is_int(p18)
            v_u_16 = p18
            v_u_15 = true
            return p17;
        end;
        v14.has_web_npc_id = function(_) --[[ Name: has_web_npc_id ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v14.get_web_npc_id = function(_) --[[ Name: get_web_npc_id ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        local v_u_19 = false
        local l_Tier1_0 = v_u_8.Tiers.Tier1
        local v_u_20 = 0
        local v_u_21 = 5
        v14.set_tier_and_index = function(p22, p23, p24) --[[ Name: set_tier_and_index ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (ref 3): l_Tier1_0, (ref 4): v_u_20, (ref 5): v_u_19 ]]
            v_u_6:is_enum_member(p23, v_u_8.Tiers)
            v_u_6:is_int(p24)
            l_Tier1_0 = p23
            v_u_20 = p24
            v_u_19 = true
            return p22;
        end;
        v14.set_tier_maximum_count = function(p25, p26) --[[ Name: set_tier_maximum_count ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_21 ]]
            v_u_6:is_int(p26)
            v_u_21 = p26
            return p25;
        end;
        v14.has_tier_and_index = function(_) --[[ Name: has_tier_and_index ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v14.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): l_Tier1_0 ]]
            return l_Tier1_0;
        end;
        v14.get_index = function(_) --[[ Name: get_index ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v14.get_tier_maximum_count = function(_) --[[ Name: get_tier_maximum_count ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        return v14;
    end
}
v11.new = function(_, p_u_28) --[[ Name: new ]] --[[ Line: 83 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_27, (copy 6): v_u_5, (copy 7): v_u_8, (copy 8): v_u_1, (copy 9): v_u_10, (copy 10): v_u_6, (copy 11): v_u_7, (copy 12): s_DataStoreService_0 ]]
    local v_u_29 = {}
    local l_WEBNPC_UPDATE_FREQ_SEC_0 = v_u_9.WEBNPC_UPDATE_FREQ_SEC
    local v_u_30 = v_u_2:new()
    local v_u_31 = v_u_2:new()
    local v_u_32 = 0
    local v_u_33 = v_u_2:new()
    v_u_29.api_is_loading = function(_) --[[ Name: api_is_loading ]] --[[ Line: 94 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_30 ]]
        if v_u_4.WebNPCDoWebAPIRead == true then
            return false;
        else
            return v_u_30:count() > 0;
        end;
    end;
    local function _() --[[ Name: fill_webnpc_datastore_queue ]] --[[ Line: 101 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_32, (copy 3): p_u_28, (ref 4): v_u_2, (copy 5): v_u_30, (ref 6): v_u_3, (ref 7): v_u_27, (ref 8): v_u_5, (ref 9): v_u_8 ]]
        v_u_29:datastore_api_get_webnpc_tier_alloc(function(p34) --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): p_u_28, (ref 3): v_u_2, (ref 4): v_u_30, (ref 5): v_u_3, (ref 6): v_u_27, (ref 7): v_u_5, (ref 8): v_u_8 ]]
            v_u_32 = p_u_28._api:get_global_time()
            v_u_2:remove_if(v_u_30, function(p35) --[[ Line: 105 ]]
                --[[ Upvalues: (ref 1): v_u_32 ]]
                return p35:get_queue_time() ~= v_u_32;
            end)
            local v_u_36 = v_u_3:new()
            local function _(p37) --[[ Name: queue_web_npc_datastore_request ]] --[[ Line: 110 ]]
                --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_30 ]]
                local v38 = p37:get_key()
                if not v_u_36:contains(v38) then
                    v_u_36:add_set(v38)
                    v_u_30:push_back(p37)
                end;
            end;
            local v39 = p34:get_web_npc_id() - 1
            for v40 = 0, 19 do
                local v41 = v39 - v40
                if v41 >= 0 and v41 <= v39 then
                    local v42 = v_u_27:new(v_u_32):set_web_npc_id(v41)
                    local v43 = v42:get_key()
                    if not v_u_36:contains(v43) then
                        v_u_36:add_set(v43)
                        v_u_30:push_back(v42)
                    end;
                end;
            end;
            for _ = 1, 10 do
                local v44 = v_u_5:rand_rangei(0, v39)
                if v44 >= 0 and v44 <= v39 then
                    local v45 = v_u_27:new(v_u_32):set_web_npc_id(v44)
                    local v46 = v45:get_key()
                    if not v_u_36:contains(v46) then
                        v_u_36:add_set(v46)
                        v_u_30:push_back(v45)
                    end;
                end;
            end;
            for _ = 1, 5 do
                local v47 = v_u_27:new(v_u_32):set_tier_and_index(v_u_8.Tiers.Tier2, (v_u_5:rand_rangei(0, p34:get_tier_to_index(v_u_8.Tiers.Tier2) - 1))):set_tier_maximum_count(5)
                local v48 = v47:get_key()
                if not v_u_36:contains(v48) then
                    v_u_36:add_set(v48)
                    v_u_30:push_back(v47)
                end;
            end;
            for _ = 1, 3 do
                local v49 = v_u_27:new(v_u_32):set_tier_and_index(v_u_8.Tiers.Tier3, (v_u_5:rand_rangei(0, p34:get_tier_to_index(v_u_8.Tiers.Tier3) - 1))):set_tier_maximum_count(3)
                local v50 = v49:get_key()
                if not v_u_36:contains(v50) then
                    v_u_36:add_set(v50)
                    v_u_30:push_back(v49)
                end;
            end;
        end)
    end;
    local function f_load_queued_webnpc_datastore_request() --[[ Name: load_queued_webnpc_datastore_request ]] --[[ Line: 170 ]]
        --[[ Upvalues: (copy 1): v_u_31, (copy 2): v_u_30, (copy 3): v_u_29, (ref 4): v_u_5, (ref 5): v_u_1, (ref 6): v_u_2, (copy 7): v_u_33 ]]
        if v_u_31:count() > 0 then
            return;
        elseif v_u_30:count() == 0 then
            return;
        else
            local v_u_51 = v_u_30:pop_front()
            local v_u_52 = v_u_51:get_queue_time()
            v_u_31:push_back(v_u_51)
            local function _(p53, p_u_54) --[[ Name: do_datastore_get_webnpcid_and_add_to_queue ]] --[[ Line: 183 ]]
                --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_5, (ref 3): v_u_1, (copy 4): v_u_51, (ref 5): v_u_2, (ref 6): v_u_33, (copy 7): v_u_52, (ref 8): v_u_30 ]]
                v_u_29:datastore_api_get_webnpcid_npcdata(p53, function(p_u_55) --[[ Line: 184 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_51, (copy 4): p_u_54, (ref 5): v_u_2, (ref 6): v_u_33, (ref 7): v_u_52, (ref 8): v_u_30 ]]
                    if p_u_55 == nil then
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("load_queued_webnpc_datastore_request no npc_data for id(%d)", v_u_51:get_web_npc_id())
                        end;
                        return p_u_54();
                    end;
                    v_u_2:remove_if(v_u_33, function(p56) --[[ Line: 193 ]]
                        --[[ Upvalues: (copy 1): p_u_55 ]]
                        return p56:get_webnpcid() == p_u_55:get_webnpcid();
                    end)
                    if v_u_33:count() >= 30 then
                        for v57 = 1, v_u_33:count() do
                            if v_u_33:get(v57):get_queue_time() ~= v_u_52 then
                                v_u_33:remove_at(v57)
                                break;
                            end;
                        end;
                    end;
                    p_u_55:set_queue_time(v_u_52)
                    v_u_33:push_back(p_u_55)
                    if v_u_5:is_dev_build() then
                        v_u_1:puts("load_queued_webnpc_datastore_request loaded web_npc_id key(%s) cached(%d) queued(%d)", v_u_51:get_key(), v_u_33:count(), v_u_30:count())
                    end;
                    p_u_54()
                end)
            end;
            local function f_on_request_finished() --[[ Name: on_request_finished ]] --[[ Line: 218 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (copy 3): v_u_51 ]]
                v_u_5:spawn(function() --[[ Line: 219 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (ref 3): v_u_51 ]]
                    v_u_5:wait(0.25)
                    v_u_31:remove(v_u_51)
                end)
            end;
            if v_u_51:has_web_npc_id() then
                local function v_u_58() --[[ Line: 226 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (copy 3): v_u_51 ]]
                    v_u_5:spawn(function() --[[ Line: 219 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (ref 3): v_u_51 ]]
                        v_u_5:wait(0.25)
                        v_u_31:remove(v_u_51)
                    end)
                end;
                v_u_29:datastore_api_get_webnpcid_npcdata(v_u_51:get_web_npc_id(), function(p_u_59) --[[ Line: 184 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (copy 3): v_u_51, (copy 4): v_u_58, (ref 5): v_u_2, (ref 6): v_u_33, (copy 7): v_u_52, (ref 8): v_u_30 ]]
                    if p_u_59 == nil then
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("load_queued_webnpc_datastore_request no npc_data for id(%d)", v_u_51:get_web_npc_id())
                        end;
                        return v_u_58();
                    end;
                    v_u_2:remove_if(v_u_33, function(p60) --[[ Line: 193 ]]
                        --[[ Upvalues: (copy 1): p_u_59 ]]
                        return p60:get_webnpcid() == p_u_59:get_webnpcid();
                    end)
                    if v_u_33:count() >= 30 then
                        for v61 = 1, v_u_33:count() do
                            if v_u_33:get(v61):get_queue_time() ~= v_u_52 then
                                v_u_33:remove_at(v61)
                                break;
                            end;
                        end;
                    end;
                    p_u_59:set_queue_time(v_u_52)
                    v_u_33:push_back(p_u_59)
                    if v_u_5:is_dev_build() then
                        v_u_1:puts("load_queued_webnpc_datastore_request loaded web_npc_id key(%s) cached(%d) queued(%d)", v_u_51:get_key(), v_u_33:count(), v_u_30:count())
                    end;
                    v_u_58()
                end)
                return;
            elseif v_u_51:has_tier_and_index() then
                v_u_29:datastore_api_get_tier_index_webnpcid(v_u_51:get_tier(), v_u_51:get_index(), function(p62, p63) --[[ Line: 231 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (copy 3): v_u_51, (copy 4): f_on_request_finished, (ref 5): v_u_33, (ref 6): v_u_31, (ref 7): v_u_29, (ref 8): v_u_2, (copy 9): v_u_52, (ref 10): v_u_30 ]]
                    if p62 ~= true then
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("load_queued_webnpc_datastore_request no webnpcid for tier(%d) index(%d)", v_u_51:get_tier(), v_u_51:get_index())
                        end;
                        return f_on_request_finished();
                    end;
                    for _, v64 in v_u_33:key_itr() do
                        if v64:get_webnpcid() == p63 then
                            if v_u_5:is_dev_build() then
                                v_u_1:puts("ServerWebNPCDatastoreManager:load_queued_webnpc_datastore_request(has_tier_and_index) skipping already cached webnpcid(%d) for tier(%d) index(%d)", p63, v_u_51:get_tier(), v_u_51:get_index())
                            end;
                            return f_on_request_finished();
                        end;
                    end;
                    local v65 = 0
                    for _, v66 in v_u_33:key_itr() do
                        if v66:get_tier() == v_u_51:get_tier() then
                            v65 = v65 + 1
                        end;
                    end;
                    if v_u_51:get_tier_maximum_count() <= v65 then
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("load_queued_webnpc_datastore_request skipping tier(%d) index(%d) max cached(%d)", v_u_51:get_tier(), v_u_51:get_index(), v65)
                        end;
                        return f_on_request_finished();
                    end;
                    local function v_u_67() --[[ Line: 263 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (ref 3): v_u_51 ]]
                        v_u_5:spawn(function() --[[ Line: 219 ]]
                            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (ref 3): v_u_51 ]]
                            v_u_5:wait(0.25)
                            v_u_31:remove(v_u_51)
                        end)
                    end;
                    v_u_29:datastore_api_get_webnpcid_npcdata(p63, function(p_u_68) --[[ Line: 184 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_51, (copy 4): v_u_67, (ref 5): v_u_2, (ref 6): v_u_33, (ref 7): v_u_52, (ref 8): v_u_30 ]]
                        if p_u_68 == nil then
                            if v_u_5:is_dev_build() then
                                v_u_1:puts("load_queued_webnpc_datastore_request no npc_data for id(%d)", v_u_51:get_web_npc_id())
                            end;
                            return v_u_67();
                        end;
                        v_u_2:remove_if(v_u_33, function(p69) --[[ Line: 193 ]]
                            --[[ Upvalues: (copy 1): p_u_68 ]]
                            return p69:get_webnpcid() == p_u_68:get_webnpcid();
                        end)
                        if v_u_33:count() >= 30 then
                            for v70 = 1, v_u_33:count() do
                                if v_u_33:get(v70):get_queue_time() ~= v_u_52 then
                                    v_u_33:remove_at(v70)
                                    break;
                                end;
                            end;
                        end;
                        p_u_68:set_queue_time(v_u_52)
                        v_u_33:push_back(p_u_68)
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("load_queued_webnpc_datastore_request loaded web_npc_id key(%s) cached(%d) queued(%d)", v_u_51:get_key(), v_u_33:count(), v_u_30:count())
                        end;
                        v_u_67()
                    end)
                end)
            else
                v_u_1:warnf("load_queued_webnpc_datastore_request invalid request key(%s)", v_u_51:get_key())
                v_u_5:spawn(function() --[[ Line: 219 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_31, (copy 3): v_u_51 ]]
                    v_u_5:wait(0.25)
                    v_u_31:remove(v_u_51)
                end)
            end;
        end;
    end;
    v_u_29.update = function(_, p71) --[[ Name: update ]] --[[ Line: 273 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_28, (ref 3): l_WEBNPC_UPDATE_FREQ_SEC_0, (ref 4): v_u_9, (ref 5): v_u_5, (copy 6): v_u_29, (ref 7): v_u_32, (ref 8): v_u_2, (copy 9): v_u_30, (ref 10): v_u_3, (ref 11): v_u_27, (ref 12): v_u_8, (ref 13): v_u_10, (copy 14): v_u_31, (copy 15): f_load_queued_webnpc_datastore_request ]]
        if v_u_4.WebNPCDoDatastoreAPIRead == true then
            if not p_u_28._player_manager:is_shutting_down() then
                if l_WEBNPC_UPDATE_FREQ_SEC_0 >= v_u_9.WEBNPC_UPDATE_FREQ_SEC then
                    l_WEBNPC_UPDATE_FREQ_SEC_0 = 0
                    v_u_5:ptry(function() --[[ Line: 279 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_29, (ref 3): v_u_32, (ref 4): p_u_28, (ref 5): v_u_2, (ref 6): v_u_30, (ref 7): v_u_3, (ref 8): v_u_27, (ref 9): v_u_5, (ref 10): v_u_8 ]]
                        if v_u_4.DebugDisableDatastoreWebNPCLoad ~= true then
                            v_u_29:datastore_api_get_webnpc_tier_alloc(function(p72) --[[ Line: 102 ]]
                                --[[ Upvalues: (ref 1): v_u_32, (ref 2): p_u_28, (ref 3): v_u_2, (ref 4): v_u_30, (ref 5): v_u_3, (ref 6): v_u_27, (ref 7): v_u_5, (ref 8): v_u_8 ]]
                                v_u_32 = p_u_28._api:get_global_time()
                                v_u_2:remove_if(v_u_30, function(p73) --[[ Line: 105 ]]
                                    --[[ Upvalues: (ref 1): v_u_32 ]]
                                    return p73:get_queue_time() ~= v_u_32;
                                end)
                                local v_u_74 = v_u_3:new()
                                local function _(p75) --[[ Name: queue_web_npc_datastore_request ]] --[[ Line: 110 ]]
                                    --[[ Upvalues: (copy 1): v_u_74, (ref 2): v_u_30 ]]
                                    local v76 = p75:get_key()
                                    if not v_u_74:contains(v76) then
                                        v_u_74:add_set(v76)
                                        v_u_30:push_back(p75)
                                    end;
                                end;
                                local v77 = p72:get_web_npc_id() - 1
                                for v78 = 0, 19 do
                                    local v79 = v77 - v78
                                    if v79 >= 0 and v79 <= v77 then
                                        local v80 = v_u_27:new(v_u_32):set_web_npc_id(v79)
                                        local v81 = v80:get_key()
                                        if not v_u_74:contains(v81) then
                                            v_u_74:add_set(v81)
                                            v_u_30:push_back(v80)
                                        end;
                                    end;
                                end;
                                for _ = 1, 10 do
                                    local v82 = v_u_5:rand_rangei(0, v77)
                                    if v82 >= 0 and v82 <= v77 then
                                        local v83 = v_u_27:new(v_u_32):set_web_npc_id(v82)
                                        local v84 = v83:get_key()
                                        if not v_u_74:contains(v84) then
                                            v_u_74:add_set(v84)
                                            v_u_30:push_back(v83)
                                        end;
                                    end;
                                end;
                                for _ = 1, 5 do
                                    local v85 = v_u_27:new(v_u_32):set_tier_and_index(v_u_8.Tiers.Tier2, (v_u_5:rand_rangei(0, p72:get_tier_to_index(v_u_8.Tiers.Tier2) - 1))):set_tier_maximum_count(5)
                                    local v86 = v85:get_key()
                                    if not v_u_74:contains(v86) then
                                        v_u_74:add_set(v86)
                                        v_u_30:push_back(v85)
                                    end;
                                end;
                                for _ = 1, 3 do
                                    local v87 = v_u_27:new(v_u_32):set_tier_and_index(v_u_8.Tiers.Tier3, (v_u_5:rand_rangei(0, p72:get_tier_to_index(v_u_8.Tiers.Tier3) - 1))):set_tier_maximum_count(3)
                                    local v88 = v87:get_key()
                                    if not v_u_74:contains(v88) then
                                        v_u_74:add_set(v88)
                                        v_u_30:push_back(v87)
                                    end;
                                end;
                            end)
                        end;
                    end)
                else
                    l_WEBNPC_UPDATE_FREQ_SEC_0 = l_WEBNPC_UPDATE_FREQ_SEC_0 + v_u_10:TimescaleToDeltaTime(p71)
                end;
                if v_u_31:count() == 0 and v_u_30:count() > 0 then
                    v_u_5:ptry(function() --[[ Line: 288 ]]
                        --[[ Upvalues: (ref 1): f_load_queued_webnpc_datastore_request ]]
                        f_load_queued_webnpc_datastore_request()
                    end)
                end;
            end;
        else
            return;
        end;
    end;
    v_u_29.dsapi_get_webnpcs = function(_, p_u_89) --[[ Name: dsapi_get_webnpcs ]] --[[ Line: 294 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_28, (ref 3): v_u_2, (copy 4): v_u_33, (ref 5): v_u_8 ]]
        if v_u_4.WebNPCDoWebAPIRead == true then
            p_u_28._api:api_get_webnpcs(function(p90) --[[ Line: 296 ]]
                --[[ Upvalues: (copy 1): p_u_89 ]]
                p_u_89(p90)
            end)
        end;
        if v_u_4.WebNPCDoDatastoreAPIRead == true then
            local v91 = v_u_2:new()
            for _, v92 in v_u_33:key_itr() do
                v91:push_back(v92)
            end;
            p_u_89(v_u_8.NPCData:list_to_table(v91))
        end;
    end;
    v_u_29.dsapi_buy_webnpc = function(p_u_93, p_u_94, p_u_95, p96, p_u_97, p_u_98, p_u_99) --[[ Name: dsapi_buy_webnpc ]] --[[ Line: 315 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (ref 3): v_u_7, (ref 4): v_u_4, (copy 5): p_u_28, (ref 6): v_u_5 ]]
        v_u_6:is_int(p_u_94)
        v_u_6:is_enum_member(p_u_95, v_u_8.Tiers)
        v_u_6:is_string(p96)
        v_u_6:is_string(p_u_97)
        v_u_6:is_int(p_u_98)
        local v_u_100 = v_u_7.Builder:new()
        local v_u_101 = false
        local v_u_102 = nil
        if v_u_4.WebNPCDoWebAPIWrite == true then
            v_u_100:begin()
            p_u_28._api:api_buy_webnpc(p_u_94, p_u_95, p96, p_u_97, p_u_98, function(p103, p104) --[[ Line: 334 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_101, (ref 3): v_u_102, (copy 4): v_u_100 ]]
                if v_u_4.WebNPCDoWebAPIRead == true then
                    v_u_101 = p103
                    v_u_102 = p104
                end;
                v_u_100:finish()
            end)
        end;
        if v_u_4.WebNPCDoDatastoreAPIWrite == true then
            v_u_100:begin()
            p_u_93:datastore_api_allocate_tier_webnpcid_index(p_u_95, function(p105, p106) --[[ Line: 346 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_28, (copy 3): p_u_94, (ref 4): v_u_8, (copy 5): p_u_97, (copy 6): p_u_95, (copy 7): p_u_98, (ref 8): v_u_7, (copy 9): p_u_93, (ref 10): v_u_4, (ref 11): v_u_101, (ref 12): v_u_102, (copy 13): v_u_100 ]]
                local v_u_107 = "Player"
                v_u_5:ptry(function() --[[ Line: 348 ]]
                    --[[ Upvalues: (ref 1): v_u_107, (ref 2): p_u_28, (ref 3): p_u_94 ]]
                    v_u_107 = p_u_28._player_manager:id_to_player(p_u_94).Name
                end)
                local v_u_108 = v_u_8.NPCData:new(p105, v_u_107, p_u_94, p_u_97, p_u_95, "", p_u_98)
                local v_u_109 = v_u_7.Builder:new()
                v_u_109:begin()
                p_u_93:datastore_api_write_webnpcid_npcdata(p105, v_u_108, function() --[[ Line: 364 ]]
                    --[[ Upvalues: (copy 1): v_u_109 ]]
                    v_u_109:finish()
                end)
                v_u_109:begin()
                p_u_93:datastore_api_write_tier_index_webnpcid(p_u_95, p106, p105, function() --[[ Line: 369 ]]
                    --[[ Upvalues: (copy 1): v_u_109 ]]
                    v_u_109:finish()
                end)
                v_u_109:begin()
                p_u_93:datastore_api_update_playerid_created(p_u_94, function(p110) --[[ Line: 376 ]]
                    --[[ Upvalues: (copy 1): v_u_108 ]]
                    p110:push_front(v_u_108)
                    while p110:count() > 500 do
                        p110:pop_back()
                    end;
                end, function() --[[ Line: 382 ]]
                    --[[ Upvalues: (copy 1): v_u_109 ]]
                    v_u_109:finish()
                end)
                v_u_109:wait_for_finish(function() --[[ Line: 387 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_101, (ref 3): v_u_102, (copy 4): v_u_108, (ref 5): v_u_100 ]]
                    if v_u_4.WebNPCDoDatastoreAPIRead == true then
                        v_u_101 = true
                        v_u_102 = v_u_108:to_table()
                    end;
                    v_u_100:finish()
                end)
            end)
        end;
        v_u_100:wait_for_finish(function() --[[ Line: 397 ]]
            --[[ Upvalues: (copy 1): p_u_99, (ref 2): v_u_101, (ref 3): v_u_102 ]]
            p_u_99(v_u_101, v_u_102)
        end)
    end;
    v_u_29.dsapi_webnpc_increment_comment_count = function(p111, p_u_112) --[[ Name: dsapi_webnpc_increment_comment_count ]] --[[ Line: 402 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_28, (ref 3): v_u_1 ]]
        if v_u_4.WebNPCDoWebAPIWrite == true then
            p_u_28._api:api_webnpc_increment_comment_count(p_u_112)
        end;
        if v_u_4.WebNPCDoDatastoreAPIWrite == true then
            p111:datastore_api_update_webnpcid_npcdata(p_u_112, function(p113) --[[ Line: 407 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_112 ]]
                if p113 == nil then
                    return v_u_1:warnf("dsapi_webnpc_increment_comment_count no npc_data for id(%d)", p_u_112);
                end;
                p113:set_comment_count(p113:get_comment_count() + 1)
            end)
        end;
    end;
    v_u_29.dsapi_webnpc_increment_like_count = function(p114, p_u_115) --[[ Name: dsapi_webnpc_increment_like_count ]] --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_28, (ref 3): v_u_1 ]]
        if v_u_4.WebNPCDoWebAPIWrite == true then
            p_u_28._api:api_webnpc_increment_like_count(p_u_115)
        end;
        if v_u_4.WebNPCDoDatastoreAPIWrite == true then
            p114:datastore_api_update_webnpcid_npcdata(p_u_115, function(p116) --[[ Line: 419 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_115 ]]
                if p116 == nil then
                    return v_u_1:warnf("dsapi_webnpc_increment_like_count no npc_data for id(%d)", p_u_115);
                end;
                p116:set_like_count(p116:get_like_count() + 1)
            end)
        end;
    end;
    v_u_29.dsapi_player_get_webnpcs = function(p117, p118, p_u_119) --[[ Name: dsapi_player_get_webnpcs ]] --[[ Line: 426 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_28, (ref 3): v_u_8 ]]
        if v_u_4.WebNPCDoWebAPIRead == true then
            p_u_28._api:api_player_get_webnpcs(p118, function(p120) --[[ Line: 428 ]]
                --[[ Upvalues: (copy 1): p_u_119 ]]
                p_u_119(p120)
            end)
        end;
        if v_u_4.WebNPCDoDatastoreAPIRead == true then
            p117:datastore_api_get_playerid_created(p118, function(p121) --[[ Line: 433 ]]
                --[[ Upvalues: (copy 1): p_u_119, (ref 2): v_u_8 ]]
                p_u_119(v_u_8.NPCData:list_to_table(p121))
            end)
        end;
    end;
    v_u_29.dsapi_get_webnpcid_npc_data = function(p122, p123, p_u_124) --[[ Name: dsapi_get_webnpcid_npc_data ]] --[[ Line: 439 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_8 ]]
        if v_u_4.WebNPCDoWebAPIRead == true then
            p_u_124(v_u_8.NPCData:new_default())
        end;
        if v_u_4.WebNPCDoDatastoreAPIRead == true then
            p122:datastore_api_get_webnpcid_npcdata(p123, function(p125) --[[ Line: 445 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_124 ]]
                local v126 = false
                if p125 == nil then
                    p125 = v_u_8.NPCData:new_default()
                else
                    v126 = true
                end;
                p_u_124(p125, v126)
            end)
        end;
    end;
    local v_u_127 = s_DataStoreService_0:GetDataStore("WebNPCDatastore")
    local v_u_128 = {}
    v_u_128.new = function(_) --[[ Name: new ]] --[[ Line: 513 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_8, (ref 3): v_u_6 ]]
        local v129 = {}
        local v_u_130 = 0
        local v_u_131 = v_u_3:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 518 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_131 ]]
            for _, v132 in v_u_8:all_tiers_list():key_itr() do
                v_u_131:add(v132, 0)
            end;
        end;
        v129.get_web_npc_id = function(_) --[[ Name: get_web_npc_id ]] --[[ Line: 524 ]]
            --[[ Upvalues: (ref 1): v_u_130 ]]
            return v_u_130;
        end;
        v129.set_web_npc_id = function(_, p133) --[[ Name: set_web_npc_id ]] --[[ Line: 525 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_130 ]]
            v_u_6:is_int(p133)
            v_u_130 = p133
        end;
        v129.increment_web_npc_id = function(_) --[[ Name: increment_web_npc_id ]] --[[ Line: 526 ]]
            --[[ Upvalues: (ref 1): v_u_130 ]]
            v_u_130 = v_u_130 + 1
        end;
        v129.get_tier_to_index = function(_, p134) --[[ Name: get_tier_to_index ]] --[[ Line: 528 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (copy 3): v_u_131 ]]
            v_u_6:is_enum_member(p134, v_u_8.Tiers)
            return v_u_131:get(p134);
        end;
        v129.set_tier_to_index = function(_, p135, p136) --[[ Name: set_tier_to_index ]] --[[ Line: 532 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (copy 3): v_u_131 ]]
            v_u_6:is_enum_member(p135, v_u_8.Tiers)
            v_u_6:is_int(p136)
            v_u_131:add(p135, p136)
        end;
        v129.increment_tier_index = function(_, p137) --[[ Name: increment_tier_index ]] --[[ Line: 537 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (copy 3): v_u_131 ]]
            v_u_6:is_enum_member(p137, v_u_8.Tiers)
            v_u_131:add(p137, v_u_131:get(p137) + 1)
        end;
        v129.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 542 ]]
            --[[ Upvalues: (ref 1): v_u_130, (ref 2): v_u_8, (copy 3): v_u_131 ]]
            local v138 = {
                ["WebNPCID"] = v_u_130
            }
            for _, v139 in v_u_8:all_tiers_list():key_itr() do
                v138["Tier_" .. tostring(v139)] = v_u_131:get(v139)
            end;
            return v138;
        end;
        f_cons()
        return v129;
    end;
    v_u_128.from_table = function(_, p140) --[[ Name: from_table ]] --[[ Line: 556 ]]
        --[[ Upvalues: (copy 1): v_u_128, (ref 2): v_u_8 ]]
        local v141 = v_u_128:new()
        if typeof(p140.WebNPCID) == "number" then
            v141:set_web_npc_id(p140.WebNPCID)
        end;
        for _, v142 in v_u_8:all_tiers_list():key_itr() do
            local v143 = "Tier_" .. tostring(v142)
            if typeof(p140[v143]) == "number" then
                v141:set_tier_to_index(v142, p140[v143])
            end;
        end;
        return v141;
    end;
    local function _() --[[ Name: web_npc_tier_alloc_key ]] --[[ Line: 568 ]]
        return "webnpc_tier_alloc";
    end;
    v_u_29.datastore_api_get_webnpc_tier_alloc = function(_, p_u_144) --[[ Name: datastore_api_get_webnpc_tier_alloc ]] --[[ Line: 570 ]]
        --[[ Upvalues: (copy 1): p_u_28, (copy 2): v_u_127, (copy 3): v_u_128 ]]
        p_u_28._datastore_api:do_datastore_get(v_u_127, "webnpc_tier_alloc", function(p145, p146) --[[ Line: 574 ]]
            --[[ Upvalues: (ref 1): v_u_128, (copy 2): p_u_144 ]]
            local v147 = v_u_128:new()
            if p145 and p146 ~= nil then
                v147 = v_u_128:from_table(p146)
            end;
            p_u_144(v147)
        end)
    end;
    local function _(p_u_148) --[[ Name: datastore_api_update_webnpc_tier_alloc ]] --[[ Line: 584 ]]
        --[[ Upvalues: (copy 1): p_u_28, (copy 2): v_u_127, (copy 3): v_u_128 ]]
        p_u_28._datastore_api:do_datastore_update(v_u_127, "webnpc_tier_alloc", function(p149) --[[ Line: 588 ]]
            --[[ Upvalues: (ref 1): v_u_128, (copy 2): p_u_148 ]]
            local v150 = v_u_128:new()
            if p149 ~= nil then
                v150 = v_u_128:from_table(p149)
            end;
            p_u_148(v150)
            return v150:to_table();
        end)
    end;
    v_u_29.datastore_api_allocate_tier_webnpcid_index = function(_, p_u_151, p_u_152) --[[ Name: datastore_api_allocate_tier_webnpcid_index ]] --[[ Line: 599 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (ref 3): v_u_5, (copy 4): p_u_28, (copy 5): v_u_127, (copy 6): v_u_128 ]]
        v_u_6:is_enum_member(p_u_151, v_u_8.Tiers)
        local function v_u_156(p153) --[[ Line: 601 ]]
            --[[ Upvalues: (copy 1): p_u_151, (ref 2): v_u_5, (copy 3): p_u_152 ]]
            local v_u_154 = p153:get_web_npc_id()
            p153:increment_web_npc_id()
            local v_u_155 = p153:get_tier_to_index(p_u_151)
            p153:increment_tier_index(p_u_151)
            v_u_5:spawn(function() --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): p_u_152, (copy 2): v_u_154, (copy 3): v_u_155 ]]
                p_u_152(v_u_154, v_u_155)
            end)
        end;
        p_u_28._datastore_api:do_datastore_update(v_u_127, "webnpc_tier_alloc", function(p157) --[[ Line: 588 ]]
            --[[ Upvalues: (ref 1): v_u_128, (copy 2): v_u_156 ]]
            local v158 = v_u_128:new()
            if p157 ~= nil then
                v158 = v_u_128:from_table(p157)
            end;
            v_u_156(v158)
            return v158:to_table();
        end)
    end;
    local function _(p159) --[[ Name: webnpcid_info_key ]] --[[ Line: 631 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        v_u_6:is_int(p159)
        return string.format("webnpcid%d_info", p159);
    end;
    v_u_29.datastore_api_write_webnpcid_npcdata = function(_, p160, p161, p162) --[[ Name: datastore_api_write_webnpcid_npcdata ]] --[[ Line: 636 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_28, (copy 3): v_u_127 ]]
        v_u_6:is_int(p160)
        local l__datastore_api_0 = p_u_28._datastore_api
        local v163 = v_u_127
        v_u_6:is_int(p160)
        l__datastore_api_0:do_datastore_set(v163, string.format("webnpcid%d_info", p160), p161:to_table(), p162)
    end;
    v_u_29.datastore_api_get_webnpcid_npcdata = function(_, p164, p_u_165) --[[ Name: datastore_api_get_webnpcid_npcdata ]] --[[ Line: 646 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_28, (copy 3): v_u_127, (ref 4): v_u_8 ]]
        v_u_6:is_int(p164)
        local l__datastore_api_1 = p_u_28._datastore_api
        local v166 = v_u_127
        v_u_6:is_int(p164)
        l__datastore_api_1:do_datastore_get(v166, string.format("webnpcid%d_info", p164), function(p167, p168) --[[ Line: 651 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_165 ]]
            local v169
            if p167 and p168 ~= nil then
                v169 = v_u_8.NPCData:from_table(p168)
            else
                v169 = nil
            end;
            p_u_165(v169)
        end)
    end;
    v_u_29.datastore_api_update_webnpcid_npcdata = function(_, p170, p_u_171, p_u_172) --[[ Name: datastore_api_update_webnpcid_npcdata ]] --[[ Line: 661 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_28, (copy 3): v_u_127, (ref 4): v_u_8 ]]
        v_u_6:is_int(p170)
        local v_u_173 = nil
        local l__datastore_api_2 = p_u_28._datastore_api
        local v174 = v_u_127
        v_u_6:is_int(p170)
        l__datastore_api_2:do_datastore_update(v174, string.format("webnpcid%d_info", p170), function(p175) --[[ Line: 667 ]]
            --[[ Upvalues: (copy 1): p_u_171, (ref 2): v_u_173, (ref 3): v_u_8 ]]
            if p175 == nil then
                p_u_171(nil)
                return nil;
            end;
            v_u_173 = v_u_8.NPCData:from_table(p175)
            p_u_171(v_u_173)
            return v_u_173:to_table();
        end, function() --[[ Line: 676 ]]
            --[[ Upvalues: (copy 1): p_u_172, (ref 2): v_u_173 ]]
            if p_u_172 ~= nil then
                p_u_172(v_u_173)
            end;
        end)
    end;
    local function _(p176, p177) --[[ Name: webnpc_tier_index_key ]] --[[ Line: 693 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8 ]]
        v_u_6:is_enum_member(p176, v_u_8.Tiers)
        v_u_6:is_int(p177)
        return string.format("tier%d_index%d", p176, p177);
    end;
    v_u_29.datastore_api_write_tier_index_webnpcid = function(_, p178, p179, p180, p181) --[[ Name: datastore_api_write_tier_index_webnpcid ]] --[[ Line: 699 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (copy 3): p_u_28, (copy 4): v_u_127 ]]
        v_u_6:is_enum_member(p178, v_u_8.Tiers)
        v_u_6:is_int(p179)
        v_u_6:is_int(p180)
        local l__datastore_api_3 = p_u_28._datastore_api
        local v182 = v_u_127
        v_u_6:is_enum_member(p178, v_u_8.Tiers)
        v_u_6:is_int(p179)
        l__datastore_api_3:do_datastore_set(v182, string.format("tier%d_index%d", p178, p179), {
            ["Tier"] = p178,
            ["Index"] = p179,
            ["WebNPCID"] = p180
        }, p181)
    end;
    v_u_29.datastore_api_get_tier_index_webnpcid = function(_, p183, p184, p_u_185) --[[ Name: datastore_api_get_tier_index_webnpcid ]] --[[ Line: 715 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (copy 3): p_u_28, (copy 4): v_u_127 ]]
        v_u_6:is_enum_member(p183, v_u_8.Tiers)
        v_u_6:is_int(p184)
        local l__datastore_api_4 = p_u_28._datastore_api
        local v186 = v_u_127
        v_u_6:is_enum_member(p183, v_u_8.Tiers)
        v_u_6:is_int(p184)
        l__datastore_api_4:do_datastore_get(v186, string.format("tier%d_index%d", p183, p184), function(p187, p188) --[[ Line: 721 ]]
            --[[ Upvalues: (copy 1): p_u_185 ]]
            local v189, v190
            if p187 and (p188 ~= nil and typeof(p188.WebNPCID) == "number") then
                v189 = p188.WebNPCID
                v190 = true
            else
                v190 = false
                v189 = 0
            end;
            p_u_185(v190, v189)
        end)
    end;
    local function _(p191) --[[ Name: playerid_created_key ]] --[[ Line: 742 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        v_u_6:is_int(p191)
        return string.format("playerid%d_created", p191);
    end;
    v_u_29.datastore_api_update_playerid_created = function(_, p192, p_u_193, p_u_194) --[[ Name: datastore_api_update_playerid_created ]] --[[ Line: 747 ]]
        --[[ Upvalues: (copy 1): p_u_28, (copy 2): v_u_127, (ref 3): v_u_6, (ref 4): v_u_2, (ref 5): v_u_8 ]]
        local l__datastore_api_5 = p_u_28._datastore_api
        local v195 = v_u_127
        v_u_6:is_int(p192)
        l__datastore_api_5:do_datastore_update(v195, string.format("playerid%d_created", p192), function(p196) --[[ Line: 751 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_8, (copy 3): p_u_193 ]]
            local v197 = v_u_2:new()
            if p196 ~= nil then
                v197 = v_u_8.NPCData:table_to_list(p196)
            end;
            p_u_193(v197)
            return v_u_8.NPCData:list_to_table(v197);
        end, function() --[[ Line: 759 ]]
            --[[ Upvalues: (copy 1): p_u_194 ]]
            if p_u_194 then
                p_u_194()
            end;
        end)
    end;
    v_u_29.datastore_api_get_playerid_created = function(_, p198, p_u_199) --[[ Name: datastore_api_get_playerid_created ]] --[[ Line: 765 ]]
        --[[ Upvalues: (copy 1): p_u_28, (copy 2): v_u_127, (ref 3): v_u_6, (ref 4): v_u_2, (ref 5): v_u_8 ]]
        local l__datastore_api_6 = p_u_28._datastore_api
        local v200 = v_u_127
        v_u_6:is_int(p198)
        l__datastore_api_6:do_datastore_get(v200, string.format("playerid%d_created", p198), function(p201, p202) --[[ Line: 769 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_8, (copy 3): p_u_199 ]]
            local v203 = v_u_2:new()
            if p201 and p202 ~= nil then
                v203 = v_u_8.NPCData:table_to_list(p202)
            end;
            p_u_199(v203)
        end)
    end;
    return v_u_29;
end;
return v11;
