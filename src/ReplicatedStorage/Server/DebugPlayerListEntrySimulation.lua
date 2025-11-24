-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_3 = require(game.ReplicatedStorage.Shared.PlayerListEntry)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v8 = {}
local v_u_19 = {
    ["new"] = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_7, (copy 4): v_u_3 ]]
        local v10 = {}
        v10.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 17 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            return p_u_9;
        end;
        local l_Lobby_0 = v_u_2.Lobby
        v10.get_activity = function(_) --[[ Name: get_activity ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): l_Lobby_0 ]]
            return l_Lobby_0;
        end;
        local v_u_11 = v_u_4:invalid_songkey()
        v10.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v10.start_lobby = function(_) --[[ Name: start_lobby ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): l_Lobby_0, (ref 2): v_u_2, (ref 3): v_u_11, (ref 4): v_u_4 ]]
            l_Lobby_0 = v_u_2.Lobby
            v_u_11 = v_u_4:invalid_songkey()
        end;
        local v_u_12 = 0
        local v_u_13 = 0
        local v_u_14 = 0
        v10.start_matchmaking = function(_, p15, p16) --[[ Name: start_matchmaking ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): l_Lobby_0, (ref 3): v_u_2, (ref 4): v_u_13, (ref 5): v_u_14 ]]
            v_u_11 = p15
            l_Lobby_0 = v_u_2.MatchMaking
            v_u_13 = p16
            v_u_14 = 0
        end;
        v10.get_matchmaking_time = function(_) --[[ Name: get_matchmaking_time ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v10.start_match = function(_) --[[ Name: start_match ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): l_Lobby_0, (ref 2): v_u_2, (ref 3): v_u_12 ]]
            l_Lobby_0 = v_u_2.Match
            v_u_12 = 0
        end;
        v10.is_match_over = function(_) --[[ Name: is_match_over ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_11, (ref 3): v_u_12 ]]
            return not v_u_4:singleton():contains_key(v_u_11) and true or v_u_12 >= v_u_4:singleton():songkey_get_approx_length_sec(v_u_11);
        end;
        v10.update = function(_, p17) --[[ Name: update ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): l_Lobby_0, (ref 3): v_u_2, (ref 4): v_u_14, (ref 5): v_u_12 ]]
            local v18 = v_u_7:TimescaleToDeltaTime(p17)
            if l_Lobby_0 == v_u_2.MatchMaking then
                v_u_14 = v_u_14 + v18
            elseif l_Lobby_0 == v_u_2.Match then
                v_u_12 = v_u_12 + v18
            end;
        end;
        v10.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_9, (ref 3): l_Lobby_0, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13 ]]
            return v_u_3:new("Player" .. tostring(p_u_9), p_u_9, l_Lobby_0, v_u_11, math.floor(v_u_12 * 1000), p_u_9 * 100, v_u_13):to_table();
        end;
        return v10;
    end
}
v8.new = function(_, _) --[[ Name: new ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_19, (copy 6): v_u_3 ]]
    local v20 = {}
    local v_u_21 = v_u_6:new()
    local v_u_22 = v_u_5:new()
    local v_u_23 = v_u_5:new()
    local v_u_24 = v_u_5:new()
    local v_u_25 = 1
    local function f_start_matchmaking_if_able() --[[ Name: start_matchmaking_if_able ]] --[[ Line: 91 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_4, (copy 5): v_u_23 ]]
        if v_u_22:count() > 3 then
            v_u_22:shuffle()
            local v26 = v_u_5:new()
            local v27 = v_u_1:rand_rangei(1, 4)
            for _ = 1, v27 do
                v26:push_back((v_u_22:pop_back()))
            end;
            local v28 = v_u_4:singleton():all_keys():random()
            for _, v29 in v26:key_itr() do
                v29:start_matchmaking(v28, v27)
            end;
            v_u_23:push_back(v26)
            return v26;
        end;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_25, (copy 3): v_u_21, (copy 4): v_u_22, (copy 5): f_start_matchmaking_if_able ]]
        for _ = 1, 20 do
            local v30 = v_u_19:new(v_u_25)
            v_u_25 = v_u_25 + 1
            v_u_21:add(v30:get_player_id(), v30)
            v_u_22:push_back(v30)
        end;
        f_start_matchmaking_if_able()
    end;
    v20.update = function(_, p31) --[[ Name: update ]] --[[ Line: 130 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_22, (copy 3): v_u_21, (ref 4): v_u_19, (ref 5): v_u_25, (copy 6): f_start_matchmaking_if_able, (ref 7): v_u_5, (copy 8): v_u_23, (copy 9): v_u_24 ]]
        if v_u_1:rand_rangei(1, 30) == 1 and v_u_22:count() > 1 then
            v_u_22:shuffle()
            v_u_21:remove(v_u_22:pop_back():get_player_id())
        end;
        if v_u_1:rand_rangei(1, 30) == 1 and v_u_21:count() < 20 then
            local v32 = v_u_19:new(v_u_25)
            v_u_25 = v_u_25 + 1
            v_u_21:add(v32:get_player_id(), v32)
            v_u_22:push_back(v32)
        end;
        if v_u_1:rand_rangei(1, 30) == 1 then
            f_start_matchmaking_if_able()
        end;
        v_u_5:remove_if(v_u_23, function(p33) --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if p33:get(1):get_matchmaking_time() <= 1 then
                return false;
            end;
            v_u_24:push_back(p33)
            for _, v34 in p33:key_itr() do
                v34:start_match()
            end;
            return true;
        end)
        v_u_5:remove_if(v_u_24, function(p35) --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            if not p35:get(1):is_match_over() then
                return false;
            end;
            for _, v36 in p35:key_itr() do
                v36:start_lobby()
                v_u_22:push_back(v36)
            end;
            return true;
        end)
        for _, v37 in v_u_21:key_itr() do
            v37:update(p31)
        end;
    end;
    v20.client_query_player_list_fake_data_list = function(_) --[[ Name: client_query_player_list_fake_data_list ]] --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_21, (ref 3): v_u_3 ]]
        local v38 = v_u_5:new()
        for _, v39 in v_u_21:key_itr() do
            v38:push_back(v39)
        end;
        local v40 = v_u_5:new()
        for _, v41 in v38:key_itr() do
            v40:push_back(v_u_3:from_table(v41:to_table()))
        end;
        return v40;
    end;
    f_cons()
    return v20;
end;
return v8;
