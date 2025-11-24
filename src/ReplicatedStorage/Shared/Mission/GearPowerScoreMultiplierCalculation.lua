-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_2 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.MissionInfo)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["calculate_score_mission"] = function(_, p4) --[[ Name: calculate_score_mission ]] --[[ Line: 52 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3 ]]
        local v5 = p4:get_difficulty() == v_u_2.Beginner and 0.35 or (p4:get_difficulty() == v_u_2.Novice and 0.8 or (p4:get_difficulty() == v_u_2.Amateur and 1 or (p4:get_difficulty() == v_u_2.Pro and 1.5 or (p4:get_difficulty() == v_u_2.Star and 2.5 or 1))))
        p4:set_type(v_u_1.Score)
        p4:set_count(v_u_3:round_to_nearest(v5 * p4:get_song_naked_max_score(), 10000))
    end,
    ["calculate_point_total_mission"] = function(_, p6) --[[ Name: calculate_point_total_mission ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3 ]]
        local v7 = p6:get_difficulty() == v_u_2.Beginner and 2 or (p6:get_difficulty() == v_u_2.Novice and 4 or (p6:get_difficulty() == v_u_2.Amateur and 6 or (p6:get_difficulty() == v_u_2.Pro and 8 or (p6:get_difficulty() == v_u_2.Star and 14 or 1))))
        p6:set_type(v_u_1.PointTotal)
        p6:set_count(v_u_3:round_to_nearest(v7 * p6:get_song_naked_max_score(), 10000))
    end
};
