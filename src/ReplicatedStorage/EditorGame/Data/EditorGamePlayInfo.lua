-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v2 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_3 = nil
v2:require_shared(function() --[[ Line: 5 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    v_u_3 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
end)
local v_u_13 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_3 ]]
        local v4 = {}
        local v_u_5 = false
        v4.is_rewarded_play = function(_) --[[ Name: is_rewarded_play ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            return v_u_5;
        end;
        v4.set_rewarded_play = function(_, p6) --[[ Name: set_rewarded_play ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_5 ]]
            v_u_1:is_bool(p6)
            v_u_5 = p6
        end;
        local v_u_7 = 0
        v4.get_time_played_sec = function(_) --[[ Name: get_time_played_sec ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v4.set_time_played_sec = function(_, p8) --[[ Name: set_time_played_sec ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_7 ]]
            v_u_1:is_number(p8)
            v_u_7 = p8
        end;
        v4.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_7 ]]
            return {
                ["IsRewardedPlay"] = v_u_5,
                ["TimePlayedSec"] = v_u_7
            };
        end;
        local v_u_9 = v_u_3.LoadCustomMapAdditionalInfo:new()
        v4.get_load_custom_map_additional_info = function(_) --[[ Name: get_load_custom_map_additional_info ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v4.set_load_custom_map_additional_info = function(_, p10) --[[ Name: set_load_custom_map_additional_info ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9 = p10
        end;
        return v4;
    end,
    ["get_minimum_reward_time_play_sec"] = function(_) --[[ Name: get_minimum_reward_time_play_sec ]] --[[ Line: 51 ]]
        return 60;
    end,
    ["copy_over_unserialized_data"] = function(_, p11, p12) --[[ Name: copy_over_unserialized_data ]] --[[ Line: 53 ]]
        p12:set_load_custom_map_additional_info(p11:get_load_custom_map_additional_info())
    end
}
v_u_13.from_table = function(_, p14) --[[ Name: from_table ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    local v15 = v_u_13:new()
    v15:set_rewarded_play(p14.IsRewardedPlay)
    v15:set_time_played_sec(p14.TimePlayedSec)
    return v15;
end;
return v_u_13;
