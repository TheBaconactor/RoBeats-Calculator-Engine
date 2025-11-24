-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v8 = require(game.ReplicatedStorage.Shared.BezierDist)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_11 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v_u_12 = {
    ["Type"] = require(game.ReplicatedStorage.Avatar.GearStatsType)
}
local v_u_13 = v_u_1:new()
for _, v14 in pairs(v_u_12.Type) do
    v_u_13:add(v14, true)
end;
v_u_12.is_valid_type = function(_, p15) --[[ Name: is_valid_type ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13:contains(p15);
end;
local v_u_16 = {
    [v_u_12.Type.ColorBlue] = "Chill Points",
    [v_u_12.Type.ColorGreen] = "Vibe Points",
    [v_u_12.Type.ColorPurple] = "Flow Points",
    [v_u_12.Type.ColorRed] = "Rush Points",
    [v_u_12.Type.ColorOrange] = "Beat Points",
    [v_u_12.Type.NoteSpeed] = "Note Speed",
    [v_u_12.Type.PerfectTime] = "Perfect Time",
    [v_u_12.Type.PerfectPoints] = "Perfect Points",
    [v_u_12.Type.GreatTime] = "Great Time",
    [v_u_12.Type.GreatPoints] = "Great Points",
    [v_u_12.Type.OkayTime] = "Okay Time",
    [v_u_12.Type.OkayPoints] = "Okay Points",
    [v_u_12.Type.ComboThreshold] = "Combo Threshold",
    [v_u_12.Type.ComboMultiplier] = "Combo Multiplier",
    [v_u_12.Type.ComboBreakMultiplier] = "Combo Break Multiplier",
    [v_u_12.Type.FeverFillRate] = "Fever Fill Rate",
    [v_u_12.Type.FeverMultiplier] = "Fever Multiplier",
    [v_u_12.Type.FeverTime] = "Fever Time",
    [v_u_12.Type.FeverDrainRate] = "Fever Drain Rate"
}
v_u_12.type_to_name = function(_, p17) --[[ Name: type_to_name ]] --[[ Line: 51 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    return v_u_16[p17];
end;
local v_u_18 = v8:new(0, 0, 0.4, 0.1, 1, 0.8, 1, 1)
local v_u_19 = v8:new(0, 0, 0.8, 0, 0.9, 0.8, 1, 1)
local v_u_20 = v8:new(0, 0, 0, 0.4, 0.7, 0.9, 1, 1)
local v_u_21 = v8:new(0, 0, 0.2, 0.1, 0.4, 1, 1, 1)
local v_u_22 = v8:new(0, 0, 0, 0.5, 0.6, 1, 1, 1)
v_u_12.get_stat_max = function(_) --[[ Name: get_stat_max ]] --[[ Line: 72 ]]
    return 80;
end;
local function f_stat_eased_curve_extended(p23, p24, p25, p26, p27, p28) --[[ Name: stat_eased_curve_extended ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_7, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_20, (copy 6): v_u_22, (copy 7): v_u_21, (copy 8): v_u_18, (copy 9): v_u_19 ]]
    v_u_9:is_number(p23)
    v_u_9:is_number(p24)
    v_u_9:is_number(p25)
    v_u_9:is_number(p26)
    v_u_9:is_number(p27)
    v_u_9:is_number(p28)
    local v29 = 0.5
    local v30 = 0
    local v31
    if v_u_7.ExtendedGearStatCap160 == true then
        v31 = v_u_4:clamp(p28, -80, 160)
    else
        v31 = v_u_4:clamp(p28, -80, 80)
    end;
    local v32
    if v31 > 0 then
        if v31 < 40 then
            v30 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(40, 1), v31)
            v29 = v_u_20:get_y_for_distance_pct(v30)
            v32 = v_u_3:Lerp(p25, p26, v29)
        elseif v_u_7.ExtendedGearStatCap160 == true and v31 > 80 then
            v30 = v_u_3:YForPointOf2PtLine(Vector2.new(80, 0), Vector2.new(160, 1), v31)
            v29 = v_u_22:get_y_for_distance_pct(v30)
            v32 = v_u_3:Lerp(p27, p27 + (p27 - p26) * 0.35, v29)
        else
            v30 = v_u_3:YForPointOf2PtLine(Vector2.new(40, 0), Vector2.new(80, 1), v31)
            v29 = v_u_21:get_y_for_distance_pct(v30)
            v32 = v_u_3:Lerp(p26, p27, v29)
        end;
    elseif v31 < 0 then
        if v31 > -40 then
            v30 = v_u_3:YForPointOf2PtLine(Vector2.new(-40, 0), Vector2.new(0, 1), v31)
            v29 = v_u_18:get_y_for_distance_pct(v30)
            v32 = v_u_3:Lerp(p24, p25, v29)
        else
            v30 = v_u_3:YForPointOf2PtLine(Vector2.new(-80, 0), Vector2.new(-40, 1), v31)
            v29 = v_u_19:get_y_for_distance_pct(v30)
            v32 = v_u_3:Lerp(p23, p24, v29)
        end;
    else
        v32 = p25
    end;
    if v_u_4:is_finite(v32) == true then
        p25 = v32
    end;
    return p25, v31, v30, v29;
end;
v_u_12.get_notespeed_multiplier = function(_, p33) --[[ Name: get_notespeed_multiplier ]] --[[ Line: 127 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return f_stat_eased_curve_extended(1.8, 1.55, 1, 0.5, 0.35, p33[v_u_12.Type.NoteSpeed]);
end;
v_u_12.get_perfect_upper_lower_time = function(_, p34) --[[ Name: get_perfect_upper_lower_time ]] --[[ Line: 132 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    local v35 = p34[v_u_12.Type.PerfectTime]
    return f_stat_eased_curve_extended(0, 10, 40, 120, 140, v35), f_stat_eased_curve_extended(0, -5, -20, -60, -80, v35);
end;
v_u_12.get_great_upper_lower_time = function(_, p36) --[[ Name: get_great_upper_lower_time ]] --[[ Line: 139 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    local v37 = p36[v_u_12.Type.GreatTime]
    return f_stat_eased_curve_extended(0, 30, 150, 600, 700, v37), f_stat_eased_curve_extended(0, -15, -75, -300, 360, v37);
end;
v_u_12.get_okay_upper_lower_time = function(_, p38) --[[ Name: get_okay_upper_lower_time ]] --[[ Line: 146 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    local v39 = p38[v_u_12.Type.OkayTime]
    return f_stat_eased_curve_extended(0, 40, 240, 960, 1040, v39), f_stat_eased_curve_extended(0, -20, -140, -560, -640, v39);
end;
v_u_12.get_perfect_points = function(_, p40) --[[ Name: get_perfect_points ]] --[[ Line: 153 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return math.floor((f_stat_eased_curve_extended(50, 100, 200, 350, 450, p40[v_u_12.Type.PerfectPoints])));
end;
v_u_12.get_great_points = function(_, p41) --[[ Name: get_great_points ]] --[[ Line: 159 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return math.floor((f_stat_eased_curve_extended(35, 75, 150, 225, 300, p41[v_u_12.Type.GreatPoints])));
end;
v_u_12.get_okay_points = function(_, p42) --[[ Name: get_okay_points ]] --[[ Line: 165 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return math.floor((f_stat_eased_curve_extended(25, 50, 100, 150, 200, p42[v_u_12.Type.OkayPoints])));
end;
v_u_12.get_combo_thresholds = function(_, p43) --[[ Name: get_combo_thresholds ]] --[[ Line: 171 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    local v44 = f_stat_eased_curve_extended(600, 450, 100, 20, 10, p43[v_u_12.Type.ComboThreshold])
    return math.floor(v44 * 0.25), math.floor(v44 * 0.5), v44;
end;
v_u_12.get_combo_multiplier = function(_, p45) --[[ Name: get_combo_multiplier ]] --[[ Line: 182 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    local v46 = f_stat_eased_curve_extended(0, 0.25, 1, 1.4, 1.6, p45[v_u_12.Type.ComboMultiplier])
    return 1 + v46 * 0.25, 1 + v46 * 0.5, 1 + v46;
end;
v_u_12.get_continuous_combo_multiplier_for_combo = function(_, p47, p48) --[[ Name: get_continuous_combo_multiplier_for_combo ]] --[[ Line: 191 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_3 ]]
    local v49, v50, v51 = v_u_12:get_combo_thresholds(p47)
    local v52, v53, v54 = v_u_12:get_combo_multiplier(p47)
    if p48 <= v49 then
        return v_u_3:YForPointOf2PtLineP1P2X(0, 1, v49, v52, p48);
    elseif p48 <= v50 then
        return v_u_3:YForPointOf2PtLineP1P2X(v49, v52, v50, v53, p48);
    elseif p48 <= v51 then
        return v_u_3:YForPointOf2PtLineP1P2X(v50, v53, v51, v54, p48);
    else
        return v54;
    end;
end;
v_u_12.ComboMultiplierThreshold = {
    ["Threshold1"] = 1,
    ["Threshold2"] = 2,
    ["Threshold3"] = 3,
    ["Threshold4"] = 4
}
v_u_12.get_combo_threshold = function(_, p55, p56) --[[ Name: get_combo_threshold ]] --[[ Line: 212 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v57, v58, v59 = v_u_12:get_combo_thresholds(p55)
    if p56 <= v57 then
        return v_u_12.ComboMultiplierThreshold.Threshold1;
    elseif p56 <= v58 then
        return v_u_12.ComboMultiplierThreshold.Threshold2;
    elseif p56 <= v59 then
        return v_u_12.ComboMultiplierThreshold.Threshold3;
    else
        return v_u_12.ComboMultiplierThreshold.Threshold4;
    end;
end;
v_u_12.get_base_decay_rate = function(_, p60) --[[ Name: get_base_decay_rate ]] --[[ Line: 225 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return f_stat_eased_curve_extended(0, 0.05, 0.15, 0.35, 0.4, p60[v_u_12.Type.FeverTime]);
end;
v_u_12.get_fever_miss_drain_pct = function(_, p61) --[[ Name: get_fever_miss_drain_pct ]] --[[ Line: 231 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return f_stat_eased_curve_extended(0.5, 0.25, 0.1, 0.01, 0, p61[v_u_12.Type.FeverDrainRate]);
end;
v_u_12.get_fever_fill_base = function(_, p62) --[[ Name: get_fever_fill_base ]] --[[ Line: 237 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    local v63 = f_stat_eased_curve_extended(0.6, 0.5, 0.333, 0.166, 0.1, p62[v_u_12.Type.FeverFillRate])
    return v63, v63 * 2, 0;
end;
v_u_12.get_powerbar_multiplier = function(_, p64) --[[ Name: get_powerbar_multiplier ]] --[[ Line: 243 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return f_stat_eased_curve_extended(1, 1.25, 3, 4.75, 5.25, p64[v_u_12.Type.FeverMultiplier]);
end;
v_u_12.get_chain_break_multiplier = function(_, p65) --[[ Name: get_chain_break_multiplier ]] --[[ Line: 248 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): f_stat_eased_curve_extended ]]
    return f_stat_eased_curve_extended(0, 0.1, 0.5, 0.9, 1, p65[v_u_12.Type.ComboBreakMultiplier]);
end;
v_u_12.statsdict_base = function(_) --[[ Name: statsdict_base ]] --[[ Line: 254 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v66 = {}
    for _, v67 in pairs(v_u_12.Type) do
        v66[v67] = 0
    end;
    return v66;
end;
local v_u_68 = nil
v_u_12.get_imm_statsdict_base = function(_) --[[ Name: get_imm_statsdict_base ]] --[[ Line: 263 ]]
    --[[ Upvalues: (ref 1): v_u_68, (copy 2): v_u_12 ]]
    if v_u_68 == nil then
        v_u_68 = v_u_12:statsdict_base()
    end;
    return v_u_68;
end;
v_u_12.statsdict_apply_statmodifierobj = function(_, p69, p70) --[[ Name: statsdict_apply_statmodifierobj ]] --[[ Line: 270 ]]
    for v71, v72 in pairs(p70) do
        if p69[v71] == nil then
            error(string.format("GearStats:apply_obj_to_statsdict does not contain key(%s)", (tostring(v71))))
        else
            p69[v71] = p69[v71] + v72
        end;
    end;
end;
v_u_12.tier_get_color = function(_, p73) --[[ Name: tier_get_color ]] --[[ Line: 280 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    if p73 == 1 then
        return v_u_4:color3(234, 255, 98);
    elseif p73 == 2 then
        return v_u_4:color3(24, 234, 252);
    elseif p73 == 3 then
        return v_u_4:color3(238, 130, 238);
    else
        return v_u_4:color3(189, 196, 195);
    end;
end;
v_u_12.gear_attrvalue_get_color = function(_, p74) --[[ Name: gear_attrvalue_get_color ]] --[[ Line: 292 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    if p74 > 0 then
        return v_u_4:color3(56, 252, 64);
    else
        return v_u_4:color3(252, 52, 73);
    end;
end;
v_u_12.gear_upgraded_attrvalue_get_color = function(_, p75) --[[ Name: gear_upgraded_attrvalue_get_color ]] --[[ Line: 300 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    if p75 >= 0 then
        return v_u_4:color3(61, 235, 249);
    else
        return v_u_4:color3(247, 135, 100);
    end;
end;
v_u_12.gear_attrvalue_opts_get_color = function(_, p76, _, p77) --[[ Name: gear_attrvalue_opts_get_color ]] --[[ Line: 308 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    if p77 then
        return v_u_12:gear_upgraded_attrvalue_get_color(p76);
    else
        return v_u_12:gear_attrvalue_get_color(p76);
    end;
end;
v_u_12.get_note_prebuffer_time_ms = function(_, p78, p79) --[[ Name: get_note_prebuffer_time_ms ]] --[[ Line: 316 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return p78 * v_u_12:get_notespeed_multiplier(p79);
end;
v_u_12.get_powerbar_base_decay_time_seconds = function(_, p80, p81) --[[ Name: get_powerbar_base_decay_time_seconds ]] --[[ Line: 320 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return p80 / 1000 * v_u_12:get_base_decay_rate(p81);
end;
v_u_12.get_powerbar_noteresult_fill = function() --[[ Name: get_powerbar_noteresult_fill ]] --[[ Line: 324 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_6, (copy 3): v_u_7 ]]
    -- failed to decompile
    -- function 29 panicked at 'called `Option::unwrap()` on a `None` value'
end;
v_u_12.get_powerbar_noteresult_drain = function(_, p82, p83) --[[ Name: get_powerbar_noteresult_drain ]] --[[ Line: 346 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_12 ]]
    return -v_u_12:get_fever_miss_drain_pct(p83) * (p82 == v_u_6.NoteResult_Perfect and 0 or (p82 == v_u_6.NoteResult_Great and 0 or (p82 == v_u_6.NoteResult_Okay and 0.25 or (p82 == v_u_6.NoteResult_Miss and 1 or 0))));
end;
v_u_12.get_chain_break = function(_, p84, p85) --[[ Name: get_chain_break ]] --[[ Line: 361 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return math.floor(v_u_12:get_chain_break_multiplier(p85) * p84);
end;
v_u_12.get_note_times = function(_, p86, p87) --[[ Name: get_note_times ]] --[[ Line: 365 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v88 = p87 == nil and 1 or p87
    local v89, v90 = v_u_12:get_perfect_upper_lower_time(p86)
    local v91, v92 = v_u_12:get_great_upper_lower_time(p86)
    local v93, v94 = v_u_12:get_okay_upper_lower_time(p86)
    local v95 = v89 * v88
    local v96 = v90 * v88
    local v97 = v91 * v88
    local v98 = v92 * v88
    local v99 = v93 * v88
    local v100 = v94 * v88
    local v101 = v95 + v97
    local v102 = v96 + v98
    return v101 + v99, v101, v95, v96, v102, v102 + v100;
end;
v_u_12.get_note_time_obj = function(_, p103, p104) --[[ Name: get_note_time_obj ]] --[[ Line: 389 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v105, v106, v107, v108, v109, v110 = v_u_12:get_note_times(p103, p104)
    return {
        v105,
        v106,
        v107,
        v108,
        v109,
        v110
    };
end;
v_u_12.note_hit_mode_get_time_multiplier = function(_, p111) --[[ Name: note_hit_mode_get_time_multiplier ]] --[[ Line: 394 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    return p111 == v_u_11.HeldHitTail and 2 or 1;
end;
v_u_12.get_top_stats = function(_, p112) --[[ Name: get_top_stats ]] --[[ Line: 402 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    local v113 = v_u_2:new()
    for v114, v115 in pairs(p112) do
        v113:push_back({
            ["Stat"] = v114,
            ["Value"] = v115
        })
    end;
    v113:sort(function(p116, p117) --[[ Line: 410 ]]
        return math.abs(p116.Value) - math.abs(p117.Value);
    end)
    return v113;
end;
v_u_12.elemental_color_to_gearstats_type = function(_, p118) --[[ Name: elemental_color_to_gearstats_type ]] --[[ Line: 418 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_10, (copy 3): v_u_12 ]]
    v_u_9:is_enum_member(p118, v_u_10)
    if p118 == v_u_10.Blue then
        return v_u_12.Type.ColorBlue;
    elseif p118 == v_u_10.Green then
        return v_u_12.Type.ColorGreen;
    elseif p118 == v_u_10.Purple then
        return v_u_12.Type.ColorPurple;
    elseif p118 == v_u_10.Red then
        return v_u_12.Type.ColorRed;
    else
        return v_u_12.Type.ColorOrange;
    end;
end;
v_u_12.gearstats_type_to_elemental_color = function(_, p119) --[[ Name: gearstats_type_to_elemental_color ]] --[[ Line: 433 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_13, (copy 3): v_u_12, (copy 4): v_u_10 ]]
    v_u_9:is_true(v_u_13:contains(p119))
    if p119 == v_u_12.Type.ColorBlue then
        return v_u_10.Blue;
    elseif p119 == v_u_12.Type.ColorGreen then
        return v_u_10.Green;
    elseif p119 == v_u_12.Type.ColorPurple then
        return v_u_10.Purple;
    elseif p119 == v_u_12.Type.ColorRed then
        return v_u_10.Red;
    elseif p119 == v_u_12.Type.ColorOrange then
        return v_u_10.Orange;
    else
        return nil;
    end;
end;
v_u_12.get_color_point_bonus_for_noteresult_colortable_statsdict = function(_, p120, p121, p122) --[[ Name: get_color_point_bonus_for_noteresult_colortable_statsdict ]] --[[ Line: 450 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_10, (copy 3): v_u_6, (copy 4): v_u_12 ]]
    if p121:count() == 1 then
        v_u_9:is_enum_member(p121:get(1), v_u_10)
        local v123 = p120 == v_u_6.NoteResult_Perfect and 3 or (p120 == v_u_6.NoteResult_Great and 2 or (p120 == v_u_6.NoteResult_Okay and 1 or 0))
        local v124 = p122[v_u_12:elemental_color_to_gearstats_type(p121:get(1))]
        v_u_9:is_int(v124)
        return math.floor(v123 * v124), 0;
    end;
    v_u_9:is_enum_member(p121:get(1), v_u_10)
    v_u_9:is_enum_member(p121:get(2), v_u_10)
    local v125 = 0
    local v126 = 0
    if p120 == v_u_6.NoteResult_Perfect then
        v125 = 2
        v126 = 1
    elseif p120 == v_u_6.NoteResult_Great then
        v125 = 1.3333333333333333
        v126 = 0.6666666666666666
    elseif p120 == v_u_6.NoteResult_Okay then
        v125 = 0.6666666666666666
        v126 = 0.3333333333333333
    end;
    local v127 = p122[v_u_12:elemental_color_to_gearstats_type(p121:get(1))]
    local v128 = p122[v_u_12:elemental_color_to_gearstats_type(p121:get(2))]
    v_u_9:is_int(v127)
    v_u_9:is_int(v128)
    return math.floor(v125 * v127), math.floor(v126 * v128);
end;
v_u_12.statsdict_get_ranked_colors = function(_, p_u_129) --[[ Name: statsdict_get_ranked_colors ]] --[[ Line: 492 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_12, (copy 3): v_u_10 ]]
    local v130 = v_u_2:new()
    for v131, _ in pairs(p_u_129) do
        local v132 = v_u_12:gearstats_type_to_elemental_color(v131)
        if v132 ~= nil then
            v130:push_back(v132)
        end;
    end;
    if v130:count() == 0 then
        v130:push_back(v_u_10.Blue)
    end;
    v130:sort(function(p133, p134) --[[ Line: 503 ]]
        --[[ Upvalues: (copy 1): p_u_129, (ref 2): v_u_12 ]]
        return p_u_129[v_u_12:elemental_color_to_gearstats_type(p133)] - p_u_129[v_u_12:elemental_color_to_gearstats_type(p134)];
    end)
    return v130;
end;
v_u_12.ranked_colors_statsdict_filter = function(_, p135, p_u_136) --[[ Name: ranked_colors_statsdict_filter ]] --[[ Line: 509 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    p135:remove_if(function(p137) --[[ Line: 510 ]]
        --[[ Upvalues: (copy 1): p_u_136, (ref 2): v_u_12 ]]
        local v138 = p_u_136[v_u_12:elemental_color_to_gearstats_type(p137)]
        return v138 == 0 and true or v138 == nil;
    end)
end;
v_u_12.get_team_buff_statmodifierobj_for_color_and_level = function(_, p139, p140) --[[ Name: get_team_buff_statmodifierobj_for_color_and_level ]] --[[ Line: 516 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v141 = {}
    local v142 = v_u_12:elemental_color_to_gearstats_type(p139)
    if p140 == 1 then
        v141[v142] = 10
        v141[v_u_12.Type.PerfectPoints] = 5
        return v141;
    end;
    if p140 == 2 then
        v141[v142] = 15
        v141[v_u_12.Type.PerfectPoints] = 10
        return v141;
    end;
    if p140 == 3 then
        v141[v142] = 20
        v141[v_u_12.Type.PerfectPoints] = 15
        return v141;
    end;
    if p140 == 4 then
        v141[v142] = 25
        v141[v_u_12.Type.PerfectPoints] = 20
        return v141;
    end;
    if p140 ~= 5 then
        if p140 >= 6 then
            v141[v142] = 35
            v141[v_u_12.Type.PerfectPoints] = 25
        end;
        return v141;
    end;
    v141[v142] = 30
    v141[v_u_12.Type.PerfectPoints] = 25
    return v141;
end;
v_u_12.playerblob_get_team_buff_statmodifierobj = function(_, p143) --[[ Name: playerblob_get_team_buff_statmodifierobj ]] --[[ Line: 541 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_9, (copy 3): v_u_12 ]]
    local l_Blue_0 = v_u_10.Blue
    if v_u_9:test_enum_member(p143.TeamBuffColor, v_u_10) then
        l_Blue_0 = p143.TeamBuffColor
    end;
    return v_u_12:get_team_buff_statmodifierobj_for_color_and_level(l_Blue_0, p143.TeamBuffLevel);
end;
v_u_12.statsdict_to_str = function(_, p144) --[[ Name: statsdict_to_str ]] --[[ Line: 549 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_12, (copy 3): v_u_4 ]]
    local v145 = v_u_1:new()
    for _, v146 in pairs(v_u_12.Type) do
        local v147 = p144[v146]
        if v147 ~= 0 and v147 ~= nil then
            v145:add(v_u_12:type_to_name(v146), v147)
        end;
    end;
    return v_u_4:table_to_string(v145:get_table());
end;
v_u_12.debug_log_stat_to_value = function(_) --[[ Name: debug_log_stat_to_value ]] --[[ Line: 560 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_12, (copy 3): v_u_5 ]]
    local v148 = v_u_1:new()
    local v149 = {}
    v149[v_u_12.Type.PerfectTime] = function(p150) --[[ Line: 562 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        local v151, v152 = v_u_12:get_perfect_upper_lower_time(p150)
        return v151 - v152;
    end
    v149[v_u_12.Type.PerfectPoints] = function(p153) --[[ Line: 566 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        return v_u_12:get_perfect_points(p153);
    end
    v149[v_u_12.Type.ComboMultiplier] = function(p154) --[[ Line: 569 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        local _, _, v155 = v_u_12:get_combo_multiplier(p154)
        return v155;
    end
    v149[v_u_12.Type.FeverFillRate] = function(p156) --[[ Line: 573 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        return v_u_12:get_fever_fill_base(p156);
    end
    v149[v_u_12.Type.FeverMultiplier] = function(p157) --[[ Line: 576 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        return v_u_12:get_powerbar_multiplier(p157);
    end
    v149[v_u_12.Type.FeverTime] = function(p158) --[[ Line: 579 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        return v_u_12:get_base_decay_rate(p158);
    end
    for v159, v160 in v148:add_table(v149):key_itr() do
        local v161 = v_u_12:type_to_name(v159)
        local v162 = string.format("-----[%s]\n", v161)
        for v163 = 0, 160 do
            local v164 = v_u_12:statsdict_base()
            v164[v159] = v163
            v162 = v162 .. string.format("\t%s[%d]\t%.5f\n", v161, v163, (v160(v164)))
        end;
        v_u_5:warnf(v162)
    end;
end;
v_u_12.ranked_color_list_and_statmodifierobj_to_string = function(_, p165, p166) --[[ Name: ranked_color_list_and_statmodifierobj_to_string ]] --[[ Line: 596 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_10 ]]
    local v167 = ""
    for v168 = 1, p165:count() do
        local v169 = p165:get(v168)
        if p166[v_u_12:elemental_color_to_gearstats_type(v169)] == nil then
            break;
        end;
        if v168 ~= 1 then
            if v168 ~= 2 then
                break;
            end;
            v167 = v167 .. ", "
        end;
        v167 = v167 .. v_u_10:color_to_name(v169)
    end;
    return v167;
end;
return v_u_12;
