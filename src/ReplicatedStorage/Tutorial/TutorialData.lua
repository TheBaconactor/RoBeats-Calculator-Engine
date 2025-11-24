-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_3 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.TutorialInfo)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
v6:require_client(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9 ]]
    v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_8 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
    v_u_9 = require(game.ReplicatedStorage.Shared.MissionInfo)
end)
local v_u_17 = {
    ["Step"] = {
        ["TutorialBegin"] = 1,
        ["TutorialGameStart"] = 2,
        ["TutorialGameEarlyQuit"] = 3,
        ["TutorialGameFinish"] = 4,
        ["TutorialSkipGame"] = 5,
        ["TutorialLoadedIntoLobby"] = 6
    },
    ["get_player_info_data"] = function(_, p10) --[[ Name: get_player_info_data ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (ref 3): v_u_9, (ref 4): v_u_8 ]]
        local v11 = v_u_1:new(v_u_2:get_local_userid(), v_u_2:get_local_username())
        v11._icon = v_u_9:difficulty_to_icon(v_u_8.Beginner)
        if p10 ~= nil then
            p10(v11)
        end;
        return 1, { v11:get_player_info(1) };
    end,
    ["get_gear_info_data_for_playerblob"] = function(_, p12, p13, p14) --[[ Name: get_gear_info_data_for_playerblob ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return { v_u_1:get_gear_info_data_for_playerblob(p12, p13, p14) };
    end,
    ["game_join_protocol_initialize"] = function(_, p15) --[[ Name: game_join_protocol_initialize ]] --[[ Line: 56 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        local v16 = p15:get_slots():get(1)
        if v16 ~= nil then
            v16._timeout = v_u_3.PRELOAD_TIMEOUT_MS
        end;
    end,
    ["get_tutorial_grant_songkey"] = function(_) --[[ Name: get_tutorial_grant_songkey ]] --[[ Line: 69 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        return v_u_4:get_tutorial_grant_songkey();
    end,
    ["get_tutorial_play_songkey"] = function(_) --[[ Name: get_tutorial_play_songkey ]] --[[ Line: 73 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        return v_u_4:get_tutorial_play_songkey();
    end
}
local v_u_18 = v_u_2:cframe_for_numtable({
    -122.0735,
    44.98616,
    -39.77615,
    0.73207,
    0.12308,
    0.67001,
    -0,
    0.98354,
    -0.18068,
    -0.68122,
    0.13227,
    0.72003
})
v_u_17.get_gear_info_data = function(_) --[[ Name: get_gear_info_data ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_5 ]]
    return v_u_17:get_gear_info_data_for_playerblob(v_u_5:get_default_playerblob(), 0, 0);
end;
v_u_17.set_camera_start = function(_) --[[ Name: set_camera_start ]] --[[ Line: 64 ]]
    --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_18 ]]
    v_u_7:set_mode(v_u_7.Mode.None)
    v_u_7:get_camera().CFrame = v_u_18
end;
return v_u_17;
