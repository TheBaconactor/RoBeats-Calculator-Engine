-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v3 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v4 = require(game.ReplicatedStorage.Shared.SPDict)
local v5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_7 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessageType)
local v_u_8 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_9 = {
    ["PC"] = 1,
    ["Mobile"] = 2,
    ["Console"] = 3
}
local v_u_10 = v4:new()
local v_u_11 = {
    ["Platform"] = {
        ["PC"] = 1,
        ["Mobile"] = 2,
        ["Console"] = 3
    }
}
for v12, v13 in pairs(v_u_9) do
    v_u_10:add(v13, v12)
end;
v_u_11.platform_get_name = function(_, p14) --[[ Name: platform_get_name ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    return v_u_10:get(p14);
end;
v_u_11.platform_get_image = function(_, p15) --[[ Name: platform_get_image ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_11 ]]
    return v_u_6:singleton():get_fevericon_for_id(v_u_11:platform_get_fevericon_id(p15)):get_image();
end;
local v_u_16 = 0
v_u_11.did_complete_match_local = function(_) --[[ Name: did_complete_match_local ]] --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_16 ]]
    return v_u_16 >= 5;
end;
v_u_11.local_flag_as_having_completed_match = function(_, p17) --[[ Name: local_flag_as_having_completed_match ]] --[[ Line: 34 ]]
    --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_11, (copy 3): v_u_8, (copy 4): v_u_7 ]]
    local v18 = v_u_16
    v_u_16 = v_u_16 + 1
    if v_u_11:playerblob_has_claimed_reward_for_platform(p17._player_blob_manager:get_player_blob(), v_u_11:get_platform_local()) == false and p17._chat:get_game_instance_channel() ~= nil then
        if v_u_16 < 5 then
            p17._chat:get_game_instance_channel():add_message_to_channel(v_u_8:new(string.format("Complete %d more song(s) to earn a reward for playing on %s!", 5 - v_u_16, v_u_11:platform_get_name(v_u_11:get_platform_local()))):set_message_type(v_u_7.System):set_icon(v_u_11:platform_get_image(v_u_11:get_platform_local())))
            return;
        end;
        if v18 < 5 and v_u_16 >= 5 then
            p17._chat:get_game_instance_channel():add_message_to_channel(v_u_8:new(string.format("For playing on %s, you have earned a reward! Claim it in the lobby.", v_u_11:platform_get_name(v_u_11:get_platform_local()))):set_message_type(v_u_7.System):set_icon(v_u_11:platform_get_image(v_u_11:get_platform_local())))
        end;
    end;
end;
v_u_11.get_platform_local = function(_) --[[ Name: get_platform_local ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_9 ]]
    if v_u_1:is_console_ui() == true then
        return v_u_9.Console;
    elseif v_u_1:is_mobile() then
        return v_u_9.Mobile;
    else
        return v_u_9.PC;
    end;
end;
v_u_11.platform_get_title_reward_id = function(_, p19) --[[ Name: platform_get_title_reward_id ]] --[[ Line: 66 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    if p19 == v_u_9.PC then
        return 109;
    end;
    if p19 == v_u_9.Mobile then
        return 110;
    end;
    if p19 == v_u_9.Console then
        return 111;
    end;
end;
v_u_11.platform_get_fevericon_id = function(_, p20) --[[ Name: platform_get_fevericon_id ]] --[[ Line: 76 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    if p20 == v_u_9.PC then
        return 168;
    end;
    if p20 == v_u_9.Mobile then
        return 169;
    end;
    if p20 == v_u_9.Console then
        return 170;
    end;
end;
local v_u_21 = v4:new()
for _, v22 in pairs(v_u_9) do
    v_u_21:add(v22, v5:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v_u_6:singleton():get_fevericon_for_id(v_u_11:platform_get_fevericon_id(v22)):get_material_id()), v3.RewardInfo:new(v3.RewardType.Titles, 1, v_u_11:platform_get_title_reward_id(v22)) }))
end;
v_u_11.platform_get_reward_desc_info_list = function(_, p23) --[[ Name: platform_get_reward_desc_info_list ]] --[[ Line: 95 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    return v_u_21:get(p23);
end;
v_u_11.playerblob_has_claimed_reward_for_platform = function(_, p24, p25) --[[ Name: playerblob_has_claimed_reward_for_platform ]] --[[ Line: 99 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_2 ]]
    return v_u_2:owns_title_id(p24, (v_u_11:platform_get_title_reward_id(p25)));
end;
return v_u_11;
