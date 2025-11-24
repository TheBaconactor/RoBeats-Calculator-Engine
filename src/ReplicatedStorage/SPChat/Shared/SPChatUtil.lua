-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_2 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v7 = {
    ["message_unfiltered_placeholder_of_length"] = function(_, p4) --[[ Name: message_unfiltered_placeholder_of_length ]] --[[ Line: 9 ]]
        return string.rep("_", p4);
    end,
    ["get_channel_message_history_count"] = function(_) --[[ Name: get_channel_message_history_count ]] --[[ Line: 13 ]]
        return 64;
    end,
    ["get_chat_cooldown_time_sec"] = function(_) --[[ Name: get_chat_cooldown_time_sec ]] --[[ Line: 15 ]]
        return 10;
    end,
    ["get_chat_cooldown_chat_amount"] = function(_) --[[ Name: get_chat_cooldown_chat_amount ]] --[[ Line: 16 ]]
        return 7;
    end,
    ["get_chat_max_message_length"] = function(_) --[[ Name: get_chat_max_message_length ]] --[[ Line: 18 ]]
        return 256;
    end,
    ["get_chat_string_param_sanity_max_length"] = function(_) --[[ Name: get_chat_string_param_sanity_max_length ]] --[[ Line: 19 ]]
        return 512;
    end,
    ["get_game_channel_color"] = function(_) --[[ Name: get_game_channel_color ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:color3(55, 234, 226);
    end,
    ["get_team_channel_color"] = function(_) --[[ Name: get_team_channel_color ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:color3(203, 195, 227);
    end,
    ["get_all_channel_color"] = function(_) --[[ Name: get_all_channel_color ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:color3(240, 239, 189);
    end,
    ["get_system_channel_color"] = function(_) --[[ Name: get_system_channel_color ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:color3(150, 150, 150);
    end,
    ["get_speaker_name_default_color"] = function(_) --[[ Name: get_speaker_name_default_color ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:color3(206, 206, 206);
    end,
    ["get_private_channel_color"] = function(_) --[[ Name: get_private_channel_color ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:color3(236, 148, 156);
    end,
    ["get_invalid_channelid"] = function(_) --[[ Name: get_invalid_channelid ]] --[[ Line: 28 ]]
        return -1;
    end,
    ["playerblob_get_chat_icon"] = function(_, p5) --[[ Name: playerblob_get_chat_icon ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
        local v6 = v_u_3:singleton():get_fevericon_for_id(p5.FeverIcon)
        if v6 and v_u_3:singleton():get_fevericon_default_available_ids_set():contains(v6:get_id()) ~= true then
            return v6:get_image(), true;
        else
            return v_u_2:difficulty_to_icon(v_u_2:playerblob_get_mission_difficulty(p5)), false;
        end;
    end
}
local v_u_8 = { "\n", "\t" }
v7.message_contains_invalid_whitespace = function(_, p9) --[[ Name: message_contains_invalid_whitespace ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    for v10 = 1, #v_u_8 do
        if string.find(p9, v_u_8[v10]) then
            return true;
        end;
    end;
    return false;
end;
return v7;
