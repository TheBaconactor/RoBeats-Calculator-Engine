-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
local v5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = {
    ["get_icon_assetid"] = function(_) --[[ Name: get_icon_assetid ]] --[[ Line: 16 ]]
        return "rbxassetid://101670777315899";
    end,
    ["get_stage_id"] = function(_) --[[ Name: get_stage_id ]] --[[ Line: 20 ]]
        return 28;
    end,
    ["get_backup_dancer_npc_id"] = function(_) --[[ Name: get_backup_dancer_npc_id ]] --[[ Line: 24 ]]
        return "NPC_Black17";
    end,
    ["server_environment_decoration_setup_enabled"] = function(_) --[[ Name: server_environment_decoration_setup_enabled ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        return v_u_4.Black17SpecialEventEnabled == true;
    end,
    ["ProgressFlags"] = {
        ["PlayAnySong"] = 0,
        ["EarnPoints1"] = 1,
        ["EarnPoints2"] = 2,
        ["EarnPoints3"] = 3,
        ["EarnPoints4"] = 4,
        ["PlayEverySong"] = 5
    },
    ["TaskFlags"] = {
        ["Song1Normal"] = 0,
        ["Song1Hard"] = 1,
        ["Song2Normal"] = 2,
        ["Song2Hard"] = 3,
        ["Song3Normal"] = 4,
        ["Song3Hard"] = 5,
        ["Song4Normal"] = 6,
        ["Song4Hard"] = 7,
        ["Song5Normal"] = 8,
        ["Song5Hard"] = 9,
        ["MultiplayerMatches1"] = 10,
        ["MultiplayerMatches2"] = 11,
        ["MultiplayerMatches3"] = 12,
        ["NoMissNormal"] = 13,
        ["NoMissHard"] = 14
    }
}
v_u_6.day_event_list_playerblob_is_event_active = function(_, _, _) --[[ Name: day_event_list_playerblob_is_event_active ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6:server_environment_decoration_setup_enabled();
end;
local v7 = v5:singleton():get_audiomod_to_modes_of_songkey(1431):get(v5.MOD_HARDMODE)
local v8 = v5:singleton():get_audiomod_to_modes_of_songkey(1433):get(v5.MOD_HARDMODE)
local v9 = v5:singleton():get_audiomod_to_modes_of_songkey(1466):get(v5.MOD_HARDMODE)
local v10 = v5:singleton():get_audiomod_to_modes_of_songkey(1468):get(v5.MOD_HARDMODE)
local v11 = v5:singleton():get_audiomod_to_modes_of_songkey(1470):get(v5.MOD_HARDMODE)
local v_u_12 = v1:new():add_set_from_table_list({
    1431,
    v7,
    1433,
    v8,
    1466,
    v9,
    1468,
    v10,
    1470,
    v11
})
v_u_6.get_all_songkeys_set = function(_) --[[ Name: get_all_songkeys_set ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return v_u_12;
end;
local v_u_13 = {
    ["PlayAnySong"] = 0,
    ["EarnPoints1"] = 1,
    ["EarnPoints2"] = 2,
    ["EarnPoints3"] = 3,
    ["EarnPoints4"] = 4,
    ["PlayEverySong"] = 5
}
local v_u_14 = v1:new({
    [v_u_13.PlayAnySong] = "Play any event song.",
    [v_u_13.EarnPoints1] = string.format("Earn %d points.", 400),
    [v_u_13.EarnPoints2] = string.format("Earn %d points.", 1000),
    [v_u_13.EarnPoints3] = string.format("Earn %d points.", 1500),
    [v_u_13.EarnPoints4] = string.format("Earn %d points.", 2000),
    [v_u_13.PlayEverySong] = "Play every difficulty of every event song."
})
v_u_6.get_progress_flag_to_description = function(_) --[[ Name: get_progress_flag_to_description ]] --[[ Line: 86 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14;
end;
local v_u_15 = {
    ["Song1Normal"] = 0,
    ["Song1Hard"] = 1,
    ["Song2Normal"] = 2,
    ["Song2Hard"] = 3,
    ["Song3Normal"] = 4,
    ["Song3Hard"] = 5,
    ["Song4Normal"] = 6,
    ["Song4Hard"] = 7,
    ["Song5Normal"] = 8,
    ["Song5Hard"] = 9,
    ["MultiplayerMatches1"] = 10,
    ["MultiplayerMatches2"] = 11,
    ["MultiplayerMatches3"] = 12,
    ["NoMissNormal"] = 13,
    ["NoMissHard"] = 14
}
local v16 = v2:new()
for _, v17 in pairs(v_u_15) do
    v16:push_back(v17)
end;
local v_u_18 = v1:new({
    [1431] = v_u_15.Song1Normal,
    [v7] = v_u_15.Song1Hard,
    [1433] = v_u_15.Song2Normal,
    [v8] = v_u_15.Song2Hard,
    [1466] = v_u_15.Song3Normal,
    [v9] = v_u_15.Song3Hard,
    [1468] = v_u_15.Song4Normal,
    [v10] = v_u_15.Song4Hard,
    [1470] = v_u_15.Song5Normal,
    [v11] = v_u_15.Song5Hard
})
v_u_6.get_songkey_to_task_flag = function(_) --[[ Name: get_songkey_to_task_flag ]] --[[ Line: 127 ]]
    --[[ Upvalues: (copy 1): v_u_18 ]]
    return v_u_18;
end;
local v_u_19 = v1:new({
    [v_u_15.Song1Normal] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(1431)),
    [v_u_15.Song1Hard] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(v7)),
    [v_u_15.Song2Normal] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(1433)),
    [v_u_15.Song2Hard] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(v8)),
    [v_u_15.Song3Normal] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(1466)),
    [v_u_15.Song3Hard] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(v9)),
    [v_u_15.Song4Normal] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(1468)),
    [v_u_15.Song4Hard] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(v10)),
    [v_u_15.Song5Normal] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(1470)),
    [v_u_15.Song5Hard] = string.format("Play \"%s\" once (Rank D or higher).", v5:singleton():get_title_for_key(v11)),
    [v_u_15.MultiplayerMatches1] = "Play 1 multiplayer (3+ player) event songs.",
    [v_u_15.MultiplayerMatches2] = "Play 3 multiplayer (3+ player) event songs.",
    [v_u_15.MultiplayerMatches3] = "Play 5 multiplayer (3+ player) event songs.",
    [v_u_15.NoMissNormal] = "No-miss any normal mode event song.",
    [v_u_15.NoMissHard] = "No-miss any hard mode event song."
})
v_u_6.get_task_flag_to_name = function(_) --[[ Name: get_task_flag_to_name ]] --[[ Line: 149 ]]
    --[[ Upvalues: (copy 1): v_u_19 ]]
    return v_u_19;
end;
local v_u_20 = v1:new({
    [v_u_15.Song1Normal] = 100,
    [v_u_15.Song1Hard] = 150,
    [v_u_15.Song2Normal] = 100,
    [v_u_15.Song2Hard] = 150,
    [v_u_15.Song3Normal] = 100,
    [v_u_15.Song3Hard] = 150,
    [v_u_15.Song4Normal] = 100,
    [v_u_15.Song4Hard] = 150,
    [v_u_15.Song5Normal] = 100,
    [v_u_15.Song5Hard] = 150,
    [v_u_15.MultiplayerMatches1] = 100,
    [v_u_15.MultiplayerMatches2] = 250,
    [v_u_15.MultiplayerMatches3] = 500,
    [v_u_15.NoMissNormal] = 250,
    [v_u_15.NoMissHard] = 500
})
v_u_6.get_task_flag_to_point_amount = function(_) --[[ Name: get_task_flag_to_point_amount ]] --[[ Line: 171 ]]
    --[[ Upvalues: (copy 1): v_u_20 ]]
    return v_u_20;
end;
local v_u_21 = {}
v_u_21.new = function(_) --[[ Name: new ]] --[[ Line: 174 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_13, (copy 3): v_u_15, (copy 4): v_u_20 ]]
    local v22 = {}
    local v_u_23 = 0
    local v_u_24 = 0
    v22.set_data = function(_, p25, p26) --[[ Name: set_data ]] --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_23, (ref 3): v_u_24 ]]
        v_u_3:is_int(p25)
        v_u_3:is_int(p26)
        v_u_23 = p25
        v_u_24 = p26
    end;
    v22.get_progress_flag = function(_, p27) --[[ Name: get_progress_flag ]] --[[ Line: 187 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_13, (ref 3): v_u_23 ]]
        v_u_3:is_enum_member(p27, v_u_13)
        return bit32.band(v_u_23, (bit32.lshift(1, p27))) ~= 0;
    end;
    v22.set_progress_flag = function(_, p28) --[[ Name: set_progress_flag ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_13, (ref 3): v_u_23 ]]
        v_u_3:is_enum_member(p28, v_u_13)
        v_u_23 = bit32.bor(v_u_23, (bit32.lshift(1, p28)))
    end;
    v22.get_task_flag = function(_, p29) --[[ Name: get_task_flag ]] --[[ Line: 190 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_15, (ref 3): v_u_24 ]]
        v_u_3:is_enum_member(p29, v_u_15)
        return bit32.band(v_u_24, (bit32.lshift(1, p29))) ~= 0;
    end;
    v22.set_task_flag = function(_, p30) --[[ Name: set_task_flag ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_15, (ref 3): v_u_24 ]]
        v_u_3:is_enum_member(p30, v_u_15)
        v_u_24 = bit32.bor(v_u_24, (bit32.lshift(1, p30)))
    end;
    v22.calculate_task_points = function(p31) --[[ Name: calculate_task_points ]] --[[ Line: 193 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        local v32 = 0
        for v33, v34 in v_u_20:key_itr() do
            if p31:get_task_flag(v33) == true then
                v32 = v32 + v34
            end;
        end;
        return v32;
    end;
    v22.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 203 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
        return {
            ["ProgressFlags"] = v_u_23,
            ["TaskFlags"] = v_u_24
        };
    end;
    return v22;
end;
v_u_21.from_table = function(_, p35) --[[ Name: from_table ]] --[[ Line: 212 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    local v36 = v_u_21:new()
    v36:set_data(p35.ProgressFlags, p35.TaskFlags)
    return v36;
end;
v_u_6.PlayerProgress = v_u_21
v_u_6.player_progress_can_claim_event_flag = function(_, p37, p38) --[[ Name: player_progress_can_claim_event_flag ]] --[[ Line: 219 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_13, (copy 3): v_u_15 ]]
    v_u_3:is_enum_member(p38, v_u_13)
    if p37:get_progress_flag(p38) == true then
        return false;
    end;
    if p38 == v_u_13.PlayAnySong then
        return p37:get_task_flag(v_u_15.Song1Normal) or p37:get_task_flag(v_u_15.Song1Hard) or (p37:get_task_flag(v_u_15.Song2Normal) or p37:get_task_flag(v_u_15.Song2Hard) or (p37:get_task_flag(v_u_15.Song3Normal) or p37:get_task_flag(v_u_15.Song3Hard)) or (p37:get_task_flag(v_u_15.Song4Normal) or p37:get_task_flag(v_u_15.Song4Hard) or (p37:get_task_flag(v_u_15.Song5Normal) or p37:get_task_flag(v_u_15.Song5Hard))));
    end;
    if p38 == v_u_13.EarnPoints1 then
        return p37:calculate_task_points() >= 400;
    end;
    if p38 == v_u_13.EarnPoints2 then
        return p37:calculate_task_points() >= 1000;
    end;
    if p38 == v_u_13.EarnPoints3 then
        return p37:calculate_task_points() >= 1500;
    end;
    if p38 == v_u_13.EarnPoints4 then
        return p37:calculate_task_points() >= 2000;
    end;
    if p38 ~= v_u_13.PlayEverySong then
        return false;
    end;
    local v39 = p37:get_task_flag(v_u_15.Song1Normal) and (p37:get_task_flag(v_u_15.Song1Hard) and p37:get_task_flag(v_u_15.Song2Normal) and (p37:get_task_flag(v_u_15.Song2Hard) and p37:get_task_flag(v_u_15.Song3Normal)) and (p37:get_task_flag(v_u_15.Song3Hard) and p37:get_task_flag(v_u_15.Song4Normal) and (p37:get_task_flag(v_u_15.Song4Hard) and p37:get_task_flag(v_u_15.Song5Normal))))
    if v39 then
        v39 = p37:get_task_flag(v_u_15.Song5Hard)
    end;
    return v39;
end;
return v_u_6;
