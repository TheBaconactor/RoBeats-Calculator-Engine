-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v5 = {}
local v_u_10 = {
    ["new"] = function(_, _) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
        local v6 = {}
        local v_u_7 = 0
        local v_u_8 = 150
        v6.get_play_count = function(_) --[[ Name: get_play_count ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v6.add_play = function(_) --[[ Name: add_play ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_3 ]]
            if v_u_7 < v_u_3:input_max_number() then
                v_u_7 = v_u_7 + 1
            end;
        end;
        v6.update = function(_, p9) --[[ Name: update ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (ref 3): v_u_7 ]]
            v_u_8 = v_u_8 - v_u_2:TimescaleToDeltaTime(p9)
            if v_u_8 <= 0 then
                v_u_7 = math.max(v_u_7 - 1, 0)
                v_u_8 = 150
            end;
        end;
        return v6;
    end
}
v5.new = function(_, _) --[[ Name: new ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_10, (copy 3): v_u_4 ]]
    local v11 = {}
    local v_u_12 = v_u_1:new()
    local v_u_13 = v_u_1:new()
    v11.add_play_for_userid = function(_, p14) --[[ Name: add_play_for_userid ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_12, (ref 2): v_u_10 ]]
        if v_u_12:contains(p14) ~= true then
            v_u_12:add(p14, v_u_10:new(p14))
        end;
        v_u_12:get(p14):add_play(p14)
    end;
    v11.get_play_count_for_userid = function(_, p15) --[[ Name: get_play_count_for_userid ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:contains(p15) ~= true and 0 or v_u_12:get(p15):get_play_count();
    end;
    v11.update = function(_, p16) --[[ Name: update ]] --[[ Line: 57 ]]
        --[[ Upvalues: (copy 1): v_u_12, (ref 2): v_u_1 ]]
        for _, v17 in v_u_12:key_itr() do
            v17:update(p16)
        end;
        v_u_1:remove_if(v_u_12, function(p18, _) --[[ Line: 61 ]]
            return p18:get_play_count() <= 0;
        end)
    end;
    v11.track_userid_last_played_song = function(_, p19, p20) --[[ Name: track_userid_last_played_song ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_13 ]]
        v_u_13:add(p19, p20)
    end;
    v11.get_userid_last_played_song = function(_, p21) --[[ Name: get_userid_last_played_song ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): v_u_13, (ref 2): v_u_4 ]]
        if v_u_13:contains(p21) == true then
            return v_u_13:get(p21);
        else
            return v_u_4:invalid_songkey();
        end;
    end;
    v11.player_disconnecting = function(_, p22) --[[ Name: player_disconnecting ]] --[[ Line: 79 ]]
        --[[ Upvalues: (copy 1): v_u_13 ]]
        v_u_13:remove(p22)
    end;
    return v11;
end;
return v5;
