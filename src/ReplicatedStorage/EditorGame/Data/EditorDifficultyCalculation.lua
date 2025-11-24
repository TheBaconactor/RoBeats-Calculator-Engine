-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_14 = {
    ["get_bucket_index"] = function(_, p5, p6) --[[ Name: get_bucket_index ]] --[[ Line: 21 ]]
        return math.floor(p5 / (p6 == nil and 15000 or p6));
    end,
    ["note_data_increment_bucket_hits"] = function(_, p7, p8, p9) --[[ Name: note_data_increment_bucket_hits ]] --[[ Line: 59 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2 ]]
        if p7:get_type() == v_u_4.NoteType.Single then
            v_u_2:counter_increment(p8, math.floor(p7:get_time_ms() / (p9 == nil and 15000 or p9)), 1)
        elseif p7:get_type() == v_u_4.NoteType.Hold then
            local v10 = p7:get_time_ms()
            local v11 = v10 + p7:get_duration()
            local v12 = math.floor(v10 / (p9 == nil and 15000 or p9))
            local v13 = math.floor(v11 / (p9 == nil and 15000 or p9))
            v_u_2:counter_increment(p8, v12, 1)
            v_u_2:counter_increment(p8, v13, 0.5)
        end;
    end
}
local function _(p15, p16) --[[ Name: get_bucket_index ]] --[[ Line: 16 ]]
    return math.floor(p15 / (p16 == nil and 15000 or p16));
end;
local function _(p17, p18, p19) --[[ Name: increment_note_type_single ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    v_u_2:counter_increment(p18, math.floor(p17 / (p19 == nil and 15000 or p19)), 1)
end;
local function _(p20, p21, p22, p23) --[[ Name: increment_note_type_held ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    local v24 = p20 + p21
    local v25 = math.floor(p20 / (p23 == nil and 15000 or p23))
    local v26 = math.floor(v24 / (p23 == nil and 15000 or p23))
    v_u_2:counter_increment(p22, v25, 1)
    v_u_2:counter_increment(p22, v26, 0.5)
end;
local v_u_27 = v_u_2:new()
v_u_14.map_data_calculate_hit_buckets = function(_, p28, p29, p30) --[[ Name: map_data_calculate_hit_buckets ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_27, (copy 2): v_u_2 ]]
    if p29 == nil then
        p29 = v_u_27
    end;
    p29:clear()
    for _, v31 in ipairs(p28.HitObjects) do
        if v31.Type == 1 then
            v_u_2:counter_increment(p29, math.floor(v31.Time / (p30 == nil and 15000 or p30)), 1)
        elseif v31.Type == 2 then
            local l_Time_0 = v31.Time
            local v32 = l_Time_0 + v31.Duration
            local v33 = math.floor(l_Time_0 / (p30 == nil and 15000 or p30))
            local v34 = math.floor(v32 / (p30 == nil and 15000 or p30))
            v_u_2:counter_increment(p29, v33, 1)
            v_u_2:counter_increment(p29, v34, 0.5)
        end;
    end;
    return p29;
end;
v_u_14.editor_game_data_note_list_calculate_hit_buckets = function(_, p35, p36, p37) --[[ Name: editor_game_data_note_list_calculate_hit_buckets ]] --[[ Line: 68 ]]
    --[[ Upvalues: (copy 1): v_u_27, (copy 2): v_u_14 ]]
    if p36 == nil then
        p36 = v_u_27
    end;
    p36:clear()
    for _, v38 in p35:key_itr() do
        v_u_14:note_data_increment_bucket_hits(v38, p36, p37)
    end;
    return p36;
end;
local function f_bucket_hits_calculate_difficulty_linear_lowend(p39, p40) --[[ Name: bucket_hits_calculate_difficulty_linear_lowend ]] --[[ Line: 82 ]]
    local v41 = (p40 == nil and 15000 or p40) / 1000
    if not p39 or p39:count() == 0 then
        return 1;
    end;
    local v42 = 0
    local v43 = 0
    for _, v44 in p39:key_itr() do
        v42 = v42 + v44 / v41
        v43 = v43 + 1
    end;
    local v45 = v42 / v43
    local v46 = nil
    for _, v47 in p39:key_itr() do
        local v48 = v47 / v41
        if not v46 or v46 < v48 then
            v46 = v48
        end;
    end;
    local v49 = 0
    for _, v50 in p39:key_itr() do
        v49 = v49 + (v50 / v41 - v45) ^ 2
    end;
    local v51 = math.floor(v45 * 1.8 + math.min(v46, 20) * 0.4 + math.sqrt(v49 / v43) * 0.4 + v43 * 0.05 + 0.5)
    return v51 < 1 and 1 or v51;
end;
local v_u_52 = {}
local function f_bucket_hits_calculate_difficulty_logarithmic_highend(p53, p54) --[[ Name: bucket_hits_calculate_difficulty_logarithmic_highend ]] --[[ Line: 121 ]]
    --[[ Upvalues: (copy 1): v_u_52 ]]
    local v55 = (p54 == nil and 15000 or p54) / 1000
    if not p53 or p53:count() == 0 then
        return 1;
    end;
    local v56 = v_u_52
    table.clear(v56)
    local v57 = 0
    local v58 = 0
    local v59 = nil
    local v60 = 0
    for _, v61 in p53:key_itr() do
        if type(v61) == "number" then
            local v62 = v61 / v55
            v57 = v57 + v62
            v58 = v58 + 1
            if v59 then
                v59 = math.max(v59, v62) or v62
            else
                v59 = v62
            end;
            if v62 > 6 then
                v60 = v60 + 1
            end;
            table.insert(v56, v62)
        end;
    end;
    local v63 = v57 / v58
    local v64 = v60 / v58
    local v65 = 0
    for _, v66 in ipairs(v56) do
        v65 = v65 + (v66 - v63) ^ 2
    end;
    return math.floor(math.log10(v63 + 1) * 15 + math.min(v59, 25) * 0.6 + math.sqrt(v65 / v58) * 0.3 + v58 * 0.02 + v64 * 1.5 + 1 + 0.5);
end;
v_u_14.bucket_hits_calculate_difficulty = function(_, p67, p68) --[[ Name: bucket_hits_calculate_difficulty ]] --[[ Line: 160 ]]
    --[[ Upvalues: (copy 1): f_bucket_hits_calculate_difficulty_linear_lowend, (copy 2): f_bucket_hits_calculate_difficulty_logarithmic_highend ]]
    local v69 = f_bucket_hits_calculate_difficulty_linear_lowend(p67, p68)
    if v69 >= 30 then
        v69 = f_bucket_hits_calculate_difficulty_logarithmic_highend(p67, p68)
    end;
    return v69;
end;
v_u_14.map_data_calculate_difficulty = function(_, p70, p71) --[[ Name: map_data_calculate_difficulty ]] --[[ Line: 168 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14:bucket_hits_calculate_difficulty(v_u_14:map_data_calculate_hit_buckets(p70, p71), p71);
end;
v_u_14.editor_game_data_note_list_calculate_difficulty = function(_, p72, p73) --[[ Name: editor_game_data_note_list_calculate_difficulty ]] --[[ Line: 174 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14:bucket_hits_calculate_difficulty(v_u_14:editor_game_data_note_list_calculate_hit_buckets(p72, p73), p73);
end;
v_u_14.run_tests = function(_, p74) --[[ Name: run_tests ]] --[[ Line: 180 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_14, (copy 3): v_u_2, (copy 4): v_u_3 ]]
    if p74 ~= true then
        return error("Client - End");
    end;
    local v_u_75 = ""
    local function f_run_test_on_song_name(p_u_76) --[[ Name: run_test_on_song_name ]] --[[ Line: 186 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_14, (ref 3): v_u_75, (ref 4): v_u_2 ]]
        local v_u_77 = v_u_1:singleton():name_to_key(p_u_76)
        v_u_1:singleton():get_data_for_key(v_u_77, function(p78) --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_75, (copy 3): p_u_76, (copy 4): v_u_77, (ref 5): v_u_1, (ref 6): v_u_2 ]]
            local v79 = v_u_14:map_data_calculate_hit_buckets(p78)
            v_u_75 = v_u_75 .. string.format("Song(%s)[%d] SongDB_Difficulty(%d) CalcDifficulty(%d)\n", p_u_76, v_u_77, v_u_1:singleton():get_difficulty_for_key(v_u_77), v_u_14:bucket_hits_calculate_difficulty(v79))
            v_u_2:for_each_key_value_sorted(v79, function(p80, p81) --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): v_u_75 ]]
                v_u_75 = v_u_75 .. string.format("\tFrom %ds to %ds: %.2f HitsPerSecond\n", p80 * 15, (p80 + 1) * 15, p81 / 15)
            end)
        end)
    end;
    print(v_u_75)
    v_u_75 = ""
    local v82 = v_u_75
    for _, v83 in v_u_3:new({
        "USAOInterstellarTravel1",
        "USAOInterstellarTravel2",
        "USAOPunish1",
        "USAOPunish2"
    }):key_itr() do
        f_run_test_on_song_name(v83)
    end;
    for v84 = 1, #v82, 16384 do
        print(v82:sub(v84, v84 + 16383))
    end;
    return error("Server - End");
end;
return v_u_14;
