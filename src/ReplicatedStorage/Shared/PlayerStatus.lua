-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_13 = {
    ["Mode"] = {
        ["Waiting"] = 0,
        ["JoinedMatchmaking"] = 1,
        ["MatchLoading"] = 2,
        ["MatchPlaying"] = 3,
        ["MatchFinished"] = 4,
        ["InSettings"] = 5
    },
    ["list_to_tablelist"] = function(_, p6) --[[ Name: list_to_tablelist ]] --[[ Line: 85 ]]
        local v7 = {}
        for v8 = 1, p6:count() do
            v7[#v7 + 1] = p6:get(v8):to_table()
        end;
        return v7;
    end,
    ["backup_cleanup"] = function(_) --[[ Name: backup_cleanup ]] --[[ Line: 99 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5 ]]
        local v_u_9 = v_u_3:new()
        return v_u_5:new(5), function(p10) --[[ Line: 101 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_3 ]]
            local s_Players_0 = game:GetService("Players")
            v_u_9:clear()
            for _, v11 in pairs(s_Players_0:GetPlayers()) do
                v_u_9:add(v11.UserId, true)
            end;
            v_u_3:remove_if(p10, function(_, p12) --[[ Line: 107 ]]
                --[[ Upvalues: (ref 1): v_u_9 ]]
                return v_u_9:contains(p12) ~= true;
            end)
        end;
    end,
    ["PlayerListFilterMode"] = {
        ["All"] = 0,
        ["Joinable"] = 1,
        ["Spectateable"] = 2
    },
    ["PlayerListOrderMode"] = {
        ["Time"] = 0,
        ["Alphabetical"] = 1
    }
}
v_u_13.new = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_13, (copy 3): v_u_1 ]]
    local v15 = {}
    v_u_4:is_int(p_u_14)
    v15.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): p_u_14 ]]
        return p_u_14;
    end;
    local v_u_16 = ""
    v15.get_player_name = function(_) --[[ Name: get_player_name ]] --[[ Line: 26 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v15.set_player_name = function(_, p17) --[[ Name: set_player_name ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_16 ]]
        v_u_4:is_string(p17)
        v_u_16 = p17
    end;
    local l_Waiting_0 = v_u_13.Mode.Waiting
    v15.get_mode = function(_) --[[ Name: get_mode ]] --[[ Line: 30 ]]
        --[[ Upvalues: (ref 1): l_Waiting_0 ]]
        return l_Waiting_0;
    end;
    v15.set_mode = function(_, p18) --[[ Name: set_mode ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_13, (ref 3): l_Waiting_0 ]]
        v_u_4:is_enum_member(p18, v_u_13.Mode)
        l_Waiting_0 = p18
    end;
    local v_u_19 = v_u_1:invalid_songkey()
    v15.get_songkey = function(_) --[[ Name: get_songkey ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        return v_u_19;
    end;
    v15.set_songkey = function(_, p20) --[[ Name: set_songkey ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_19 ]]
        v_u_4:is_int(p20)
        v_u_19 = p20
    end;
    local v_u_21 = 0
    v15.get_playback_time_sec = function(_) --[[ Name: get_playback_time_sec ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v15.set_playback_time_sec = function(_, p22) --[[ Name: set_playback_time_sec ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_21 ]]
        v_u_4:is_number(p22)
        v_u_21 = p22
    end;
    local v_u_23 = 0
    v15.get_sound_length_sec = function(_) --[[ Name: get_sound_length_sec ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    v15.set_sound_length_sec = function(_, p24) --[[ Name: set_sound_length_sec ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_23 ]]
        v_u_4:is_number(p24)
        v_u_23 = p24
    end;
    local v_u_25 = 1
    v15.get_game_slot = function(_) --[[ Name: get_game_slot ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v15.set_game_slot = function(_, p26) --[[ Name: set_game_slot ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_25 ]]
        v_u_4:is_number(p26)
        v_u_25 = p26
    end;
    local v_u_27 = CFrame.new()
    v15.get_cframe = function(_) --[[ Name: get_cframe ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v15.set_cframe = function(_, p28) --[[ Name: set_cframe ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_27 ]]
        v_u_4:is_cframe(p28)
        v_u_27 = p28
    end;
    local v_u_29 = -1
    v15.get_last_modified = function(_) --[[ Name: get_last_modified ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v15.set_last_modified = function(_, p30) --[[ Name: set_last_modified ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_29 ]]
        v_u_4:is_number(p30)
        v_u_29 = p30
    end;
    v15.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 57 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_16, (ref 3): l_Waiting_0, (ref 4): v_u_19, (ref 5): v_u_21, (ref 6): v_u_23, (ref 7): v_u_25, (ref 8): v_u_27 ]]
        return {
            ["PlayerId"] = p_u_14,
            ["PlayerName"] = v_u_16,
            ["Mode"] = l_Waiting_0,
            ["SongKey"] = v_u_19,
            ["PlaybackTimeSec"] = v_u_21,
            ["SoundLengthSec"] = v_u_23,
            ["GameSlot"] = v_u_25,
            ["CFrame"] = v_u_27
        };
    end;
    return v15;
end;
v_u_13.from_table = function(_, p31) --[[ Name: from_table ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    local v32 = v_u_13:new(p31.PlayerId)
    v32:set_player_name(p31.PlayerName)
    v32:set_mode(p31.Mode)
    v32:set_songkey(p31.SongKey)
    v32:set_playback_time_sec(p31.PlaybackTimeSec)
    v32:set_sound_length_sec(p31.SoundLengthSec)
    v32:set_game_slot(p31.GameSlot)
    v32:set_cframe(p31.CFrame)
    return v32;
end;
v_u_13.tablelist_to_list = function(_, p33) --[[ Name: tablelist_to_list ]] --[[ Line: 91 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_13 ]]
    local v34 = v_u_2:new()
    for v35 = 1, #p33 do
        v34:push_back(v_u_13:from_table(p33[v35]))
    end;
    return v34;
end;
return v_u_13;
