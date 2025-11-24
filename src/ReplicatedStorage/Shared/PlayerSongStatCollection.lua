-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Time elapsed: 10 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v21 = {
    ["Stat"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
            return {
                ["BestScore"] = 0,
                ["BestGrade"] = 0,
                ["PlayCount"] = 0
            };
        end,
        ["get_best_score"] = function(_, p22) --[[ Name: get_best_score ]] --[[ Line: 18 ]]
            return p22.BestScore;
        end,
        ["set_best_score"] = function(_, p23, p24) --[[ Name: set_best_score ]] --[[ Line: 19 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            v_u_4:is_int(p24)
            p23.BestScore = p24
        end,
        ["get_best_grade"] = function(_, p25) --[[ Name: get_best_grade ]] --[[ Line: 20 ]]
            return p25.BestGrade;
        end,
        ["set_best_grade"] = function(_, p26, p27) --[[ Name: set_best_grade ]] --[[ Line: 21 ]]
            --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3 ]]
            v_u_4:is_enum_member(p27, v_u_3.Value)
            p26.BestGrade = p27
        end,
        ["get_play_count"] = function(_, p28) --[[ Name: get_play_count ]] --[[ Line: 22 ]]
            return p28.PlayCount;
        end,
        ["set_play_count"] = function(_, p29, p30) --[[ Name: set_play_count ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            v_u_4:is_int(p30)
            p29.PlayCount = p30
        end
    },
    ["Rank"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 29 ]]
            return {
                ["Rank"] = 0,
                ["TotalCount"] = 0
            };
        end,
        ["get_rank"] = function(_, p32) --[[ Name: get_rank ]] --[[ Line: 35 ]]
            return p32.Rank;
        end,
        ["set_rank"] = function(_, p33, p34) --[[ Name: set_rank ]] --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            v_u_4:is_int(p34)
            p33.Rank = p34
        end,
        ["get_total_count"] = function(_, p35) --[[ Name: get_total_count ]] --[[ Line: 37 ]]
            return p35.TotalCount;
        end,
        ["set_total_count"] = function(_, p36, p37) --[[ Name: set_total_count ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            v_u_4:is_int(p37)
            p36.TotalCount = p37
        end
    }
}
local v_u_31 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
        return {
            ["BestScore"] = 0,
            ["BestGrade"] = 0,
            ["PlayCount"] = 0
        };
    end,
    ["get_best_score"] = function(_, p22) --[[ Name: get_best_score ]] --[[ Line: 18 ]]
        return p22.BestScore;
    end,
    ["set_best_score"] = function(_, p23, p24) --[[ Name: set_best_score ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        v_u_4:is_int(p24)
        p23.BestScore = p24
    end,
    ["get_best_grade"] = function(_, p25) --[[ Name: get_best_grade ]] --[[ Line: 20 ]]
        return p25.BestGrade;
    end,
    ["set_best_grade"] = function(_, p26, p27) --[[ Name: set_best_grade ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3 ]]
        v_u_4:is_enum_member(p27, v_u_3.Value)
        p26.BestGrade = p27
    end,
    ["get_play_count"] = function(_, p28) --[[ Name: get_play_count ]] --[[ Line: 22 ]]
        return p28.PlayCount;
    end,
    ["set_play_count"] = function(_, p29, p30) --[[ Name: set_play_count ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        v_u_4:is_int(p30)
        p29.PlayCount = p30
    end
}
local v_u_38 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 29 ]]
        return {
            ["Rank"] = 0,
            ["TotalCount"] = 0
        };
    end,
    ["get_rank"] = function(_, p32) --[[ Name: get_rank ]] --[[ Line: 35 ]]
        return p32.Rank;
    end,
    ["set_rank"] = function(_, p33, p34) --[[ Name: set_rank ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        v_u_4:is_int(p34)
        p33.Rank = p34
    end,
    ["get_total_count"] = function(_, p35) --[[ Name: get_total_count ]] --[[ Line: 37 ]]
        return p35.TotalCount;
    end,
    ["set_total_count"] = function(_, p36, p37) --[[ Name: set_total_count ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        v_u_4:is_int(p37)
        p36.TotalCount = p37
    end
}
v21.new = function(_) --[[ Name: new ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_31, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_5, (copy 7): v_u_38 ]]
    local v40 = {
        ["to_table"] = function(p39) --[[ Name: to_table ]] --[[ Line: 109 ]]
            return p39:to_json_obj();
        end
    }
    local v_u_41 = v_u_2:new()
    local v_u_42 = v_u_2:new()
    local v_u_43 = 0
    v40.get_time_last_update = function(_) --[[ Name: get_time_last_update ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        return v_u_43;
    end;
    v40.add_songkey = function(_, p44) --[[ Name: add_songkey ]] --[[ Line: 54 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): v_u_31 ]]
        if v_u_41:contains(p44) == false then
            v_u_41:add(p44, v_u_31:new())
        end;
        return v_u_41:get(p44);
    end;
    v40.get_stat_for_songkey = function(_, p45) --[[ Name: get_stat_for_songkey ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): v_u_41 ]]
        return v_u_41:get(p45);
    end;
    v40.load_from_json_obj = function(p46, p47) --[[ Name: load_from_json_obj ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_43 ]]
        for v48 = 1, #p47 do
            local v49 = p47[v48]
            local l_SongKey_0 = v49.SongKey
            if l_SongKey_0 == nil then
                v_u_1:errf("PlayerSongStatCollection:write_play_result_from_json_obj no SongKey")
            end;
            local v50 = p46:add_songkey(l_SongKey_0)
            v50.BestScore = v49.BestScore
            local l_BestGrade_0 = v49.BestGrade
            if v_u_4:test_enum_member(l_BestGrade_0, v_u_3.Value) ~= true then
                l_BestGrade_0 = v_u_3.Value.RankF
            end;
            v50.BestGrade = l_BestGrade_0
            v50.PlayCount = v49.PlayCount
        end;
        v_u_43 = tick()
    end;
    v40.to_json_obj = function(_) --[[ Name: to_json_obj ]] --[[ Line: 84 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_41, (ref 3): v_u_5, (ref 4): v_u_3 ]]
        local v51 = v_u_2:new()
        for v52, _ in v_u_41:key_itr() do
            v51:add_set(v52)
        end;
        local v53 = v_u_5:new()
        for v54, _ in v51:key_itr() do
            local v55 = {
                ["SongKey"] = v54,
                ["BestScore"] = 0,
                ["BestGrade"] = v_u_3.Value.RankF,
                ["PlayCount"] = 0
            }
            if v_u_41:contains(v54) == true then
                local v56 = v_u_41:get(v54)
                v55.BestScore = v56.BestScore
                v55.BestGrade = v56.BestGrade
                v55.PlayCount = v56.PlayCount
            end;
            v53:push_back(v55)
        end;
        return v53:get_table();
    end;
    v40.write_play_result_from_json_obj = function(p57, p58) --[[ Name: write_play_result_from_json_obj ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_43, (ref 3): v_u_4, (ref 4): v_u_3 ]]
        local l_SongKey_1 = p58.SongKey
        if l_SongKey_1 == nil then
            v_u_1:errf("PlayerSongStatCollection:write_play_result_from_json_obj no SongKey")
        end;
        v_u_43 = tick()
        local v59 = p57:add_songkey(l_SongKey_1)
        v59.BestScore = p58.BestScore
        local l_BestGrade_1 = p58.BestGrade
        if v_u_4:test_enum_member(l_BestGrade_1, v_u_3.Value) ~= true then
            l_BestGrade_1 = v_u_3.Value.RankF
        end;
        v59.BestGrade = l_BestGrade_1
        v59.PlayCount = p58.PlayCount
        return {
            ["IsNewBestScore"] = p58.IsNewBestScore,
            ["IsNewBestGrade"] = p58.IsNewBestGrade,
            ["OldScore"] = p58.OldScore,
            ["OldGrade"] = p58.BestGrade,
            ["Rank"] = p58.Rank,
            ["TotalCount"] = p58.TotalCount
        };
    end;
    v40.get_rank_for_songkey = function(_, p60) --[[ Name: get_rank_for_songkey ]] --[[ Line: 135 ]]
        --[[ Upvalues: (copy 1): v_u_42 ]]
        if v_u_42:contains(p60) == false then
            return nil, nil;
        end;
        local v61 = v_u_42:get(p60)
        return v61.Rank, v61.TotalCount;
    end;
    v40.add_rank = function(_, p62, p63, p64) --[[ Name: add_rank ]] --[[ Line: 143 ]]
        --[[ Upvalues: (copy 1): v_u_42, (ref 2): v_u_38, (ref 3): v_u_43 ]]
        if v_u_42:contains(p62) == false then
            v_u_42:add(p62, v_u_38:new())
        end;
        local v65 = v_u_42:get(p62)
        v65.Rank = p63
        v65.TotalCount = p64
        v_u_43 = tick()
    end;
    v40.load_from_rank_request_json_obj = function(p66, p67) --[[ Name: load_from_rank_request_json_obj ]] --[[ Line: 153 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_43 ]]
        local l_SongKey_2 = p67.SongKey
        local l_Rank_0 = p67.Rank
        local l_TotalCount_0 = p67.TotalCount
        v_u_4:is_int(p67.Rank)
        v_u_4:is_int(p67.TotalCount)
        p66:add_rank(l_SongKey_2, l_Rank_0, l_TotalCount_0)
        v_u_43 = tick()
        return l_SongKey_2;
    end;
    return v40;
end;
return v21;
