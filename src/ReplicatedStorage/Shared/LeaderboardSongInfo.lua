-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = {
    ["get_max_weekly_entries"] = function(_) --[[ Name: get_max_weekly_entries ]] --[[ Line: 8 ]]
        return 4;
    end,
    ["Score"] = {}
}
v_u_2.Score.new = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
    return {
        ["PlayerName"] = "",
        ["RbxID"] = 0,
        ["Score"] = 0,
        ["GearMult"] = 0,
        ["Place"] = 0,
        ["Valid"] = false,
        ["Attempts"] = 0
    };
end;
v_u_2.Score.copy = function(_, p3) --[[ Name: copy ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
    local v4 = v_u_2.Score:new()
    v4.PlayerName = p3.PlayerName
    v4.RbxID = p3.RbxID
    v4.Score = p3.Score
    v4.GearMult = p3.GearMult
    v4.Place = p3.Place
    v4.Valid = p3.Valid
    v4.Attempts = p3.Attempts
    v_u_1:is_string(v4.PlayerName)
    v_u_1:is_int(v4.RbxID)
    v_u_1:is_int(v4.Score)
    v_u_1:is_number(v4.GearMult)
    v_u_1:is_int(v4.Place)
    v_u_1:is_bool(v4.Valid)
    v_u_1:is_int(v4.Attempts)
    return v4;
end;
v_u_2.Score.from_table = function(_, p5) --[[ Name: from_table ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.Score:copy(p5);
end;
v_u_2.Score.to_table = function(_, p6) --[[ Name: to_table ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.Score:copy(p6);
end;
v_u_2.new = function(_) --[[ Name: new ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        ["SongKey"] = 0,
        ["TimeRemaining"] = 0,
        ["TotalParticipants"] = 0,
        ["SongIndex"] = 0,
        ["MaxSongIndex"] = 0,
        ["LeaderboardPlaces"] = {},
        ["YouDisplayAbove"] = v_u_2.Score:new(),
        ["YouDisplay"] = v_u_2.Score:new(),
        ["YouDisplayBelow"] = v_u_2.Score:new(),
        ["IsEntered"] = false,
        ["EntryPrice"] = 0,
        ["EntryPriceType"] = 0
    };
end;
v_u_2.from_leaderboard_info_table = function(_, p7) --[[ Name: from_leaderboard_info_table ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
    local v8 = v_u_2:new()
    v8.SongKey = p7.SongKey
    v8.TimeRemaining = p7.TimeRemaining
    v8.TotalParticipants = p7.TotalParticipants
    v8.SongIndex = p7.SongIndex
    v8.MaxSongIndex = p7.MaxSongIndex
    v_u_1:is_table(p7.LeaderboardPlaces)
    for v9 = 1, #p7.LeaderboardPlaces do
        v8.LeaderboardPlaces[v9] = v_u_2.Score:copy(p7.LeaderboardPlaces[v9])
    end;
    v8.EntryPrice = p7.EntryPrice
    v8.EntryPriceType = p7.EntryPriceType
    v_u_1:is_int(v8.SongKey)
    v_u_1:is_number(v8.TimeRemaining)
    v_u_1:is_int(v8.TotalParticipants)
    v_u_1:is_int(v8.SongIndex)
    v_u_1:is_int(v8.MaxSongIndex)
    v_u_1:is_int(v8.EntryPrice)
    v_u_1:is_int(v8.EntryPriceType)
    return v8;
end;
v_u_2.from_info_table_and_player_leaderboard_info = function(_, p10, p11) --[[ Name: from_info_table_and_player_leaderboard_info ]] --[[ Line: 99 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
    local v12 = v_u_2:from_leaderboard_info_table(p10)
    v_u_2:leaderboard_song_info_apply_player_leaderboard_info(v12, p11)
    v_u_1:is_bool(v12.IsEntered)
    return v12;
end;
v_u_2.leaderboard_song_info_apply_player_leaderboard_info = function(_, p13, p14) --[[ Name: leaderboard_song_info_apply_player_leaderboard_info ]] --[[ Line: 108 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    p13.IsEntered = p14.IsEntered
    p13.YouDisplayAbove = v_u_2.Score:copy(p14.YouDisplayAbove)
    p13.YouDisplay = v_u_2.Score:copy(p14.YouDisplay)
    p13.YouDisplayBelow = v_u_2.Score:copy(p14.YouDisplayBelow)
end;
return v_u_2;
