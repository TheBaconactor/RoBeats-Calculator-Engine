-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_6 = {
    ["ES_END_SCORE"] = 1,
    ["ES_END_NAKEDSCORE"] = 2,
    ["ES_END_CHAIN"] = 3,
    ["ES_END_ACCURACY"] = 4,
    ["ES_END_PERFECTCOUNT"] = 5,
    ["ES_END_GREATCOUNT"] = 6,
    ["ES_END_OKAYCOUNT"] = 7,
    ["ES_END_MISSCOUNT"] = 8,
    ["ES_END_MAXCHAIN"] = 9,
    ["ES_END_FEVERPERCENTAGE"] = 10,
    ["ES_END_AUTOPLAY"] = 11,
    ["ES_GAME_SCORE"] = 12,
    ["ES_GAME_NAKEDSCORE"] = 13,
    ["ES_GAME_CHAIN"] = 14,
    ["ES_GAME_ACCURACY"] = 15,
    ["ES_GAME_RAISECHAINBROKEN"] = 16,
    ["ES_GAME_NOTERESULT"] = 17,
    ["ES_GAME_AUTOPLAY"] = 18,
    ["ES_NOTESEQ_TIMESTART"] = 19,
    ["ES_NOTESEQ_TIME"] = 20,
    ["ES_NOTESEQ_NOTEINDEX"] = 21,
    ["ES_NOTESEQ_NOTERESULT"] = 22,
    ["ES_NOTESEQ_HITTIMEOFFSET"] = 23,
    ["ES_NOTESEQ_EVENTS"] = 24,
    ["ES_NOTESEQ_ISFEVER"] = 25,
    ["ES_NOTESEQ_TIMEEND"] = 26,
    ["ES_NOTESEQ_SCORESTART"] = 27,
    ["ES_NOTESEQ_SCOREEND"] = 28,
    ["ES_NOTESEQ_COMBOSTART"] = 29,
    ["ES_NOTESEQ_COMBOEND"] = 30,
    ["ES_NOTESEQ_TRACKINDEX"] = 31,
    ["ES_NOTESEQ_NOTE_HIT_MODE"] = 32,
    ["ES_NOTESEQ_FEVER_PCT"] = 33,
    ["ES_END_COMBOMAX"] = 34,
    ["ES_NOTESEQ_ACCURACY"] = 35,
    ["ES_FN_TMP1"] = 40,
    ["ES_FN_TMP2"] = 41,
    ["ES_FN_TMP3"] = 42,
    ["ES_FN_TMP4"] = 43,
    ["ES_NOTESEQ_NAKED_SCORE"] = 44,
    ["ES_NOTESEQ_NAKED_COMBO"] = 45,
    ["ES_NOTESEQ_NAKED_ISFEVER"] = 46,
    ["ES_NOTESEQ_NAKED_FEVER_PCT"] = 47
}
local v_u_7 = v2:new()
local v_u_8 = v2:new()
local v_u_9 = v2:new()
local v_u_10 = v2:new()
local v_u_11 = v_u_3:new()
local v_u_12 = false
v_u_6.es_fn_enabled = function(_, p13) --[[ Name: es_fn_enabled ]] --[[ Line: 68 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = p13
end;
v_u_6.initialize_with_table_checksum = function(_, p14) --[[ Name: initialize_with_table_checksum ]] --[[ Line: 72 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_5 ]]
    v_u_6:initialize_with_seed(v_u_1:table_checksum(v_u_1:hash_creator(v_u_5.ES_STR_SEED), p14, "EventString"))
end;
v_u_6.initialize_with_seed = function(_, p15) --[[ Name: initialize_with_seed ]] --[[ Line: 78 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_6, (copy 5): v_u_10, (copy 6): v_u_7, (copy 7): v_u_8, (copy 8): v_u_11 ]]
    v_u_9:clear()
    local v_u_16 = p15
    local v_u_17 = v_u_3:new()
    local function f_generate_new_hash(p18) --[[ Name: generate_new_hash ]] --[[ Line: 83 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_16, (copy 3): v_u_17 ]]
        local v19 = v_u_1:hash_creator(v_u_16)((tostring(p18)))
        while v_u_17:contains(v19) == true do
            v_u_16 = v_u_16 + 1
            v19 = v_u_1:hash_creator(v_u_16)((tostring(p18)))
        end;
        return v19;
    end;
    for _, v20 in pairs(v_u_6) do
        if typeof(v20) == "number" then
            local v21 = f_generate_new_hash(v20)
            v_u_9:add(v20, v21)
            v_u_10:add(v21, v20)
            v_u_17:push_back(v21)
            local v22 = f_generate_new_hash(v20)
            v_u_7:add(v20, v22)
            v_u_8:add(v22, v20)
            v_u_11:push_back(v20)
            v_u_17:push_back(v22)
        end;
    end;
end;
local function _(p23) --[[ Line: 113 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_4 ]]
    if v_u_9:contains(p23) ~= true then
        v_u_4:warnf("EvtStr no(%d)", p23)
        v_u_4:errf("EvtStr fail")
    end;
    return v_u_9:get(p23);
end;
local function v_u_26(p24) --[[ Line: 118 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_7 ]]
    for _, v25 in pairs(p24) do
        if typeof(v25) ~= "table" then
            p24[v_u_7:get((v_u_11:random()))] = v25
        end;
    end;
end;
v_u_6.es_table_convert = function(_, p27, p28) --[[ Name: es_table_convert ]] --[[ Line: 127 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_4, (copy 3): v_u_26 ]]
    local v29 = {}
    for v30, v31 in pairs(p27) do
        if v_u_9:contains(v30) ~= true then
            v_u_4:warnf("EvtStr no(%d)", v30)
            v_u_4:errf("EvtStr fail")
        end;
        v29[v_u_9:get(v30)] = v31
    end;
    if p28 ~= false then
        v_u_26(v29)
    end;
    return v29;
end;
local function v_u_38(_, p32, _, p33, _, p34, _) --[[ Line: 138 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    local v35 = {}
    for v36, v37 in pairs(p32) do
        if p34:contains(v36) then
            v35[p34:get(v36)] = v37
        elseif not p33:contains(v36) then
            v_u_4:errf("EventString_Deconvert unexpected hashkey(%s)", v36)
        end;
    end;
    return v35;
end;
v_u_6.es_table_deconvert = function(_, p39) --[[ Name: es_table_deconvert ]] --[[ Line: 152 ]]
    --[[ Upvalues: (copy 1): v_u_38, (copy 2): v_u_6, (copy 3): v_u_7, (copy 4): v_u_8, (copy 5): v_u_9, (copy 6): v_u_10, (copy 7): v_u_11 ]]
    return v_u_38(v_u_6, p39, v_u_7, v_u_8, v_u_9, v_u_10, v_u_11);
end;
v_u_6.es_fn_def = function(_, p40, p41, p42) --[[ Name: es_fn_def ]] --[[ Line: 156 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    p40[v_u_9:get(p41)] = p42
end;
v_u_6.es_fn_get = function(_, p43, p44) --[[ Name: es_fn_get ]] --[[ Line: 160 ]]
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_9 ]]
    return v_u_12 ~= true and function() end or p43[v_u_9:get(p44)];
end;
return v_u_6;
