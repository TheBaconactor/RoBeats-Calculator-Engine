-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["is_event_active"] = function(_, p3) --[[ Name: is_event_active ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v4, v5 = p3:is_event_type_active(v_u_1.EventType.RBChallenge)
        return v4 and v5 == 5 and true or false;
    end,
    ["is_playerblob_debug_active"] = function(_, p6) --[[ Name: is_playerblob_debug_active ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        return v_u_2:is_tester_status(p6);
    end,
    ["get_hud_button_assetid"] = function(_) --[[ Name: get_hud_button_assetid ]] --[[ Line: 19 ]]
        return "rbxassetid://10182360725";
    end
};
