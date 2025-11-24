-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v11 = {
    ["day_event_list_playerblob_is_event_active"] = function(_, p7, p8) --[[ Name: day_event_list_playerblob_is_event_active ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_4 ]]
        if v_u_6.RBGamesSpecialEventEnabled ~= true then
            return false;
        end;
        local v9, v10 = p7:is_event_type_active(v_u_1.EventType.HolidayEvent)
        return v9 and v10 == 6 and true or v_u_4:get_title_id(p8) == 16;
    end
}
local v_u_12 = {
    ["Quest1"] = 0,
    ["Quest2"] = 1,
    ["Quest3"] = 3,
    ["Item1"] = 4,
    ["Item2"] = 5,
    ["Item3"] = 6,
    ["Item4"] = 7,
    ["Item5"] = 8,
    ["CompleteAll"] = 9
}
local v_u_13 = v2:new({
    [v_u_12.Quest1] = "Complete 3 songs in a matches with 3 or more players.",
    [v_u_12.Quest2] = "Earn 500 points from tasks.",
    [v_u_12.Quest3] = "Earn 1000 points from tasks.",
    [v_u_12.Item1] = "Hidden Shine 1.",
    [v_u_12.Item2] = "Hidden Shine 2.",
    [v_u_12.Item3] = "Hidden Shine 3.",
    [v_u_12.Item4] = "Hidden Shine 4.",
    [v_u_12.Item5] = "Hidden Shine 5.",
    [v_u_12.CompleteAll] = "Completed all tasks, quests and found all shines!"
})
v11.get_progress_flag_to_description = function(_) --[[ Name: get_progress_flag_to_description ]] --[[ Line: 79 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13;
end;
local v_u_14 = {
    ["QueueSongRadio"] = 0,
    ["VoteSongRadio"] = 1,
    ["SpeakPlayerNPC"] = 3,
    ["SpectateCheerPlayer"] = 4,
    ["Complete3MultiplayerSongs"] = 5,
    ["WinMultiplayerMatch"] = 6,
    ["CompleteSongMission"] = 7,
    ["Complete5Songs"] = 8,
    ["CompleteNoMissMission"] = 10,
    ["Complete10Songs"] = 11,
    ["CompleteSongDiffA"] = 12,
    ["CompleteSongDiffB"] = 13,
    ["CompleteSongDiffC"] = 14,
    ["CompleteExtendedCut"] = 15,
    ["Complete10MultiplayerSongs"] = 16
}
local v_u_15 = v3:new()
for _, v16 in pairs(v_u_14) do
    v_u_15:push_back(v16)
end;
local v_u_17 = v2:new({
    [v_u_14.QueueSongRadio] = "Queue a song on RoBeats radio.",
    [v_u_14.VoteSongRadio] = "Vote on a song on RoBeats radio.",
    [v_u_14.SpeakPlayerNPC] = "Find a player NPC with rewards.",
    [v_u_14.SpectateCheerPlayer] = "Cheer on another player while spectating.",
    [v_u_14.Complete3MultiplayerSongs] = "Complete 3 different songs in a match with 3 or more players.",
    [v_u_14.WinMultiplayerMatch] = "Win a match with 3 or more players.",
    [v_u_14.CompleteSongMission] = "Complete a song-based mission.",
    [v_u_14.Complete5Songs] = "Complete 5 or more songs of any difficulty.",
    [v_u_14.CompleteNoMissMission] = "Complete a no-miss mission.",
    [v_u_14.Complete10Songs] = "Complete 10 songs of any difficulty.",
    [v_u_14.CompleteSongDiffA] = "Earn a Rank \'B\' or above on a song of difficulty 1 to 10.",
    [v_u_14.CompleteSongDiffB] = "Earn a Rank \'B\' or above on a song of difficulty 11 to 21.",
    [v_u_14.CompleteSongDiffC] = "Earn a Rank \'B\' or above on a song of difficulty 22 or above.",
    [v_u_14.CompleteExtendedCut] = "Earn a Rank \'B\' or above on an Extended Cut song.",
    [v_u_14.Complete10MultiplayerSongs] = "Complete 10 songs in a match with 3 or more players."
})
v11.get_task_flag_to_name = function(_) --[[ Name: get_task_flag_to_name ]] --[[ Line: 120 ]]
    --[[ Upvalues: (copy 1): v_u_17 ]]
    return v_u_17;
end;
local v_u_18 = v2:new({
    [v_u_14.QueueSongRadio] = 50,
    [v_u_14.VoteSongRadio] = 50,
    [v_u_14.SpeakPlayerNPC] = 50,
    [v_u_14.SpectateCheerPlayer] = 50,
    [v_u_14.Complete3MultiplayerSongs] = 250,
    [v_u_14.WinMultiplayerMatch] = 250,
    [v_u_14.CompleteSongMission] = 50,
    [v_u_14.Complete5Songs] = 150,
    [v_u_14.CompleteNoMissMission] = 150,
    [v_u_14.Complete10Songs] = 250,
    [v_u_14.CompleteSongDiffA] = 50,
    [v_u_14.CompleteSongDiffB] = 100,
    [v_u_14.CompleteSongDiffC] = 150,
    [v_u_14.CompleteExtendedCut] = 200,
    [v_u_14.Complete10MultiplayerSongs] = 500
})
v11.get_task_flag_to_point_amount = function(_) --[[ Name: get_task_flag_to_point_amount ]] --[[ Line: 139 ]]
    --[[ Upvalues: (copy 1): v_u_18 ]]
    return v_u_18;
end;
local v_u_19 = {}
v_u_19.new = function(_) --[[ Name: new ]] --[[ Line: 142 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_12, (copy 3): v_u_14, (copy 4): v_u_18 ]]
    local v20 = {}
    local v_u_21 = 0
    local v_u_22 = 0
    v20.set_data = function(_, p23, p24) --[[ Name: set_data ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_21, (ref 3): v_u_22 ]]
        v_u_5:is_int(p23)
        v_u_5:is_int(p24)
        v_u_21 = p23
        v_u_22 = p24
    end;
    v20.get_progress_flag = function(_, p25) --[[ Name: get_progress_flag ]] --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_12, (ref 3): v_u_21 ]]
        v_u_5:is_enum_member(p25, v_u_12)
        return bit32.band(v_u_21, (bit32.lshift(1, p25))) ~= 0;
    end;
    v20.set_progress_flag = function(_, p26) --[[ Name: set_progress_flag ]] --[[ Line: 156 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_12, (ref 3): v_u_21 ]]
        v_u_5:is_enum_member(p26, v_u_12)
        v_u_21 = bit32.bor(v_u_21, (bit32.lshift(1, p26)))
    end;
    v20.get_task_flag = function(_, p27) --[[ Name: get_task_flag ]] --[[ Line: 158 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_14, (ref 3): v_u_22 ]]
        v_u_5:is_enum_member(p27, v_u_14)
        return bit32.band(v_u_22, (bit32.lshift(1, p27))) ~= 0;
    end;
    v20.set_task_flag = function(_, p28) --[[ Name: set_task_flag ]] --[[ Line: 159 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_14, (ref 3): v_u_22 ]]
        v_u_5:is_enum_member(p28, v_u_14)
        v_u_22 = bit32.bor(v_u_22, (bit32.lshift(1, p28)))
    end;
    v20.calculate_task_points = function(p29) --[[ Name: calculate_task_points ]] --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        local v30 = 0
        for v31, v32 in v_u_18:key_itr() do
            if p29:get_task_flag(v31) == true then
                v30 = v30 + v32
            end;
        end;
        return v30;
    end;
    v20.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 171 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
        return {
            ["ProgressFlags"] = v_u_21,
            ["TaskFlags"] = v_u_22
        };
    end;
    return v20;
end;
v_u_19.from_table = function(_, p33) --[[ Name: from_table ]] --[[ Line: 180 ]]
    --[[ Upvalues: (copy 1): v_u_19 ]]
    local v34 = v_u_19:new()
    v34:set_data(p33.ProgressFlags, p33.TaskFlags)
    return v34;
end;
local function _(p35) --[[ Name: player_progress_can_claim_quest1 ]] --[[ Line: 186 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return p35:get_task_flag(v_u_14.Complete3MultiplayerSongs) == true;
end;
local function _(p36) --[[ Name: player_progress_can_claim_quest2 ]] --[[ Line: 190 ]]
    return p36:calculate_task_points() >= 500;
end;
local function _(p37) --[[ Name: player_progress_can_claim_quest3 ]] --[[ Line: 194 ]]
    return p37:calculate_task_points() >= 1000;
end;
local v40 = {
    [v_u_12.Quest2] = function(p38) --[[ Line: 200 ]]
        return p38:calculate_task_points() >= 500;
    end,
    [v_u_12.Quest3] = function(p39) --[[ Line: 201 ]]
        return p39:calculate_task_points() >= 1000;
    end
}
v40[v_u_12.Quest1] = function(p41) --[[ Line: 199 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return p41:get_task_flag(v_u_14.Complete3MultiplayerSongs) == true;
end
v40[v_u_12.CompleteAll] = function(p42) --[[ Line: 202 ]]
    --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_12 ]]
    for _, v43 in v_u_15:key_itr() do
        if p42:get_task_flag(v43) ~= true then
            return false;
        end;
    end;
    local v44
    if p42:get_progress_flag(v_u_12.Quest1) == true and (p42:get_progress_flag(v_u_12.Quest2) == true and (p42:get_progress_flag(v_u_12.Quest3) == true and (p42:get_progress_flag(v_u_12.Item1) == true and (p42:get_progress_flag(v_u_12.Item2) == true and (p42:get_progress_flag(v_u_12.Item3) == true and p42:get_progress_flag(v_u_12.Item4) == true))))) then
        v44 = p42:get_progress_flag(v_u_12.Item5) == true
    else
        v44 = false
    end;
    return v44;
end
local v_u_45 = v2:new(v40)
v11.player_progress_can_claim_event_flag = function(_, p46, p47) --[[ Name: player_progress_can_claim_event_flag ]] --[[ Line: 218 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_12, (copy 3): v_u_45 ]]
    v_u_5:is_enum_member(p47, v_u_12)
    if p46:get_progress_flag(p47) == true then
        return false;
    else
        return v_u_45:contains(p47) ~= true or v_u_45:get(p47)(p46) == true;
    end;
end;
v11.ProgressFlags = v_u_12
v11.TaskFlags = v_u_14
v11.PlayerProgress = v_u_19
return v11;
