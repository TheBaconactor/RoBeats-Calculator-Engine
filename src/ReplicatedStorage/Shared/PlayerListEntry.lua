-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_25 = {
    ["new"] = function(_, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3 ]]
        local v_u_14 = {
            ["copy_from_entry"] = function(p12, p13) --[[ Name: copy_from_entry ]] --[[ Line: 61 ]]
                p12:set_name(p13:get_name())
                p12:set_player_id(p13:get_player_id())
                p12:set_activity(p13:get_activity())
                p12:set_song_key(p13:get_song_key())
                p12:set_match_time_ms(p13:get_match_time_ms())
                p12:set_join_time(p13:get_join_time())
                p12:set_match_player_count(p13:get_match_player_count())
            end
        }
        v_u_14.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): p_u_5 ]]
            return p_u_5;
        end;
        v_u_14.set_name = function(_, p15) --[[ Name: set_name ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_5 ]]
            v_u_2:is_string(p15)
            p_u_5 = p15
        end;
        v_u_14.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): p_u_6 ]]
            return p_u_6;
        end;
        v_u_14.set_player_id = function(_, p16) --[[ Name: set_player_id ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_6 ]]
            v_u_2:is_int(p16)
            p_u_6 = p16
        end;
        v_u_14.get_activity = function(_) --[[ Name: get_activity ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): p_u_7 ]]
            return p_u_7;
        end;
        v_u_14.set_activity = function(_, p17) --[[ Name: set_activity ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_1, (ref 3): p_u_7 ]]
            v_u_2:is_enum_member(p17, v_u_1)
            p_u_7 = p17
        end;
        v_u_14.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): p_u_8 ]]
            return p_u_8;
        end;
        v_u_14.get_songkey = function(_) --[[ Name: get_songkey ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): p_u_8 ]]
            return p_u_8;
        end;
        v_u_14.set_song_key = function(_, p18) --[[ Name: set_song_key ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (ref 3): p_u_8 ]]
            v_u_2:is_true(p18 == v_u_3:invalid_songkey() and true or v_u_3:singleton():contains_key(p18))
            p_u_8 = p18
        end;
        v_u_14.get_match_time_ms = function(_) --[[ Name: get_match_time_ms ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): p_u_9 ]]
            return p_u_9;
        end;
        v_u_14.set_match_time_ms = function(_, p19) --[[ Name: set_match_time_ms ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_9 ]]
            v_u_2:is_number(p19)
            p_u_9 = p19
        end;
        v_u_14.get_join_time = function(_) --[[ Name: get_join_time ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            return p_u_10;
        end;
        v_u_14.set_join_time = function(_, p20) --[[ Name: set_join_time ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_10 ]]
            v_u_2:is_number(p20)
            p_u_10 = p20
        end;
        v_u_14.get_match_player_count = function(_) --[[ Name: get_match_player_count ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): p_u_11 ]]
            return p_u_11;
        end;
        v_u_14.get_match_playercount = function(_) --[[ Name: get_match_playercount ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): p_u_11 ]]
            return p_u_11;
        end;
        v_u_14.set_match_player_count = function(_, p21) --[[ Name: set_match_player_count ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_11 ]]
            v_u_2:is_int(p21)
            p_u_11 = p21
        end;
        v_u_14.get_song_length_ms = function(_) --[[ Name: get_song_length_ms ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_8 ]]
            return v_u_3:singleton():songkey_get_approx_length_sec(p_u_8) * 1000;
        end;
        v_u_14.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): p_u_5, (ref 2): p_u_6, (ref 3): p_u_7, (ref 4): p_u_8, (ref 5): p_u_9, (ref 6): p_u_10, (ref 7): p_u_11 ]]
            return {
                ["Name"] = p_u_5,
                ["PlayerId"] = p_u_6,
                ["Activity"] = p_u_7,
                ["SongKey"] = p_u_8,
                ["MatchTime"] = p_u_9,
                ["JoinTime"] = p_u_10,
                ["MatchPlayerCount"] = p_u_11
            };
        end;
        (function() --[[ Name: cons ]] --[[ Line: 11 ]]
            --[[ Upvalues: (ref 1): p_u_5, (copy 2): v_u_14, (ref 3): p_u_6, (ref 4): p_u_7, (ref 5): p_u_8, (ref 6): p_u_9, (ref 7): p_u_10, (ref 8): p_u_11 ]]
            if p_u_5 ~= nil then
                v_u_14:set_name(p_u_5)
            end;
            if p_u_6 ~= nil then
                v_u_14:set_player_id(p_u_6)
            end;
            if p_u_7 ~= nil then
                v_u_14:set_activity(p_u_7)
            end;
            if p_u_8 ~= nil then
                v_u_14:set_song_key(p_u_8)
            end;
            if p_u_9 ~= nil then
                v_u_14:set_match_time_ms(p_u_9)
            end;
            if p_u_10 ~= nil then
                v_u_14:set_join_time(p_u_10)
            end;
            if p_u_11 ~= nil then
                v_u_14:set_match_player_count(p_u_11)
            end;
        end)()
        return v_u_14;
    end,
    ["list_to_table"] = function(_, p22) --[[ Name: list_to_table ]] --[[ Line: 99 ]]
        local v23 = {}
        for v24 = 1, p22:count() do
            v23[v24] = p22:get(v24):to_table()
        end;
        return v23;
    end
}
v_u_25.from_table = function(_, p26) --[[ Name: from_table ]] --[[ Line: 87 ]]
    --[[ Upvalues: (copy 1): v_u_25 ]]
    return v_u_25:new(p26.Name, p26.PlayerId, p26.Activity, p26.SongKey, p26.MatchTime, p26.JoinTime, p26.MatchPlayerCount);
end;
v_u_25.table_to_list = function(_, p27) --[[ Name: table_to_list ]] --[[ Line: 107 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_25 ]]
    local v28 = v_u_4:new()
    for v29 = 1, #p27 do
        v28:push_back(v_u_25:from_table(p27[v29]))
    end;
    return v28;
end;
return v_u_25;
