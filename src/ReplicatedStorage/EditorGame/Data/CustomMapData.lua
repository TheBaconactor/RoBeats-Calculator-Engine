-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.ForwardCompatSerialization)
local v_u_18 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v5 = {}
        local v_u_6 = v_u_2:new()
        v5.get_notes = function(_) --[[ Name: get_notes ]] --[[ Line: 18 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            return v_u_6;
        end;
        local v_u_7 = v_u_2:new()
        v5.get_timing_points = function(_) --[[ Name: get_timing_points ]] --[[ Line: 21 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7;
        end;
        v5.get_hit_count = function(_) --[[ Name: get_hit_count ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_1 ]]
            local v8 = 0
            for _, v9 in v_u_6:key_itr() do
                if v9:get_type() == v_u_1.NoteType.Hold then
                    v8 = v8 + 2
                else
                    v8 = v8 + 1
                end;
            end;
            return v8;
        end;
        v5.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_7 ]]
            local v10 = {}
            for v11 = 1, v_u_6:count() do
                v10[v11] = v_u_6:get(v11):to_compressed_list()
            end;
            local v12 = {}
            for v13 = 1, v_u_7:count() do
                v12[v13] = v_u_7:get(v13):to_table()
            end;
            return {
                ["Notes"] = v10,
                ["TimingPoints"] = v12
            };
        end;
        v5.to_songdatabase_note_data = function(_) --[[ Name: to_songdatabase_note_data ]] --[[ Line: 55 ]]
            --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_7 ]]
            local v14 = {}
            for v15 = 1, v_u_6:count() do
                v14[v15] = v_u_6:get(v15):to_table()
            end;
            local v16 = {}
            for v17 = 1, v_u_7:count() do
                v16[v17] = v_u_7:get(v17):to_table()
            end;
            return {
                ["HitObjects"] = v14,
                ["TimingPoints"] = v16
            };
        end;
        return v5;
    end,
    ["get_max_note_count"] = function(_) --[[ Name: get_max_note_count ]] --[[ Line: 105 ]]
        return 7500;
    end,
    ["get_max_timing_point_count"] = function(_) --[[ Name: get_max_timing_point_count ]] --[[ Line: 106 ]]
        return 100;
    end
}
v_u_18.from_table = function(_, p_u_19) --[[ Name: from_table ]] --[[ Line: 77 ]]
    --[[ Upvalues: (copy 1): v_u_18, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_4 ]]
    local v_u_20 = v_u_18:new()
    local v21 = true
    for v_u_22 = 1, #p_u_19.Notes do
        local v23, v24 = v_u_3:try(function() --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_19, (copy 3): v_u_22, (copy 4): v_u_20 ]]
            v_u_20:get_notes():push_back((v_u_1.Note:from_compressed_list(p_u_19.Notes[v_u_22])))
        end)
        if v23 ~= true and v21 then
            v_u_4:warnf("CustomMapData:from_table Note error %s", v24)
            v21 = false
        end;
    end;
    for v_u_25 = 1, #p_u_19.TimingPoints do
        local v26, v27 = v_u_3:try(function() --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_19, (copy 3): v_u_25, (copy 4): v_u_20 ]]
            v_u_20:get_timing_points():push_back((v_u_1.TimingPoint:from_table(p_u_19.TimingPoints[v_u_25])))
        end)
        if v26 ~= true and v21 then
            v_u_4:warnf("CustomMapData:from_table TimingPoints error %s", v27)
            v21 = false
        end;
    end;
    return v_u_20;
end;
return v_u_18;
