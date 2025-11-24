-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:01 PM
-- Cached decompilation

local v_u_36 = {
    ["Lerp"] = function(_, p1, p2, p3) --[[ Name: Lerp ]] --[[ Line: 5 ]]
        return (p2 - p1) * p3 + p1;
    end,
    ["Expty"] = function(_, _, _, p4, p5) --[[ Name: Expty ]] --[[ Line: 24 ]]
        return 1 - math.exp(-(-math.log(1 - p4)) * p5);
    end,
    ["Sign"] = function(_, p6) --[[ Name: Sign ]] --[[ Line: 31 ]]
        return p6 > 0 and 1 or (p6 < 0 and -1 or 0);
    end,
    ["BezierValForT"] = function(_, p7, p8, p9, p10, p11) --[[ Name: BezierValForT ]] --[[ Line: 41 ]]
        return (1 - p11) * (1 - p11) * (1 - p11) * p7 + 3 * p11 * (1 - p11) * (1 - p11) * p8 + 3 * p11 * p11 * (1 - p11) * p9 + p11 * p11 * p11 * p10;
    end,
    ["_BezierPt2ForT"] = {
        ["X"] = 0,
        ["Y"] = 0
    },
    ["YForPointOf2PtLineP1P2X"] = function(_, p12, p13, p14, p15, p16) --[[ Name: YForPointOf2PtLineP1P2X ]] --[[ Line: 76 ]]
        local v17 = (p13 - p15) / (p12 - p14)
        return v17 * p16 + (p13 - v17 * p12);
    end,
    ["DeltaTimeToTimescale"] = function(_, p18) --[[ Name: DeltaTimeToTimescale ]] --[[ Line: 84 ]]
        return p18 / 0.016666666666666666;
    end,
    ["TimescaleToDeltaTime"] = function(_, p19) --[[ Name: TimescaleToDeltaTime ]] --[[ Line: 88 ]]
        return p19 * 0.016666666666666666;
    end,
    ["SecondsToTick"] = function(_, p20) --[[ Name: SecondsToTick ]] --[[ Line: 92 ]]
        return 0.016666666666666666 / p20;
    end,
    ["ExptValueInSeconds"] = function(_, p21, p22, p23) --[[ Name: ExptValueInSeconds ]] --[[ Line: 100 ]]
        return 1 - math.pow(p21 / p22, 1 / (60 * p23));
    end,
    ["IncrementWrap"] = function(_, p24, p25, p26) --[[ Name: IncrementWrap ]] --[[ Line: 118 ]]
        local v27 = (p24 + p25) % p26
        return v27, p24 + p25 ~= v27;
    end,
    ["IncrementClamp"] = function(_, p28, p29, p30, p31) --[[ Name: IncrementClamp ]] --[[ Line: 128 ]]
        local v32 = p28 + p29
        if p31 <= v32 then
            return p31, true;
        elseif v32 <= p30 then
            return p30, true;
        else
            return v32, false;
        end;
    end,
    ["wrap_val"] = function(_, p33, p34, p35) --[[ Name: wrap_val ]] --[[ Line: 147 ]]
        return (p33 - p34) % (p35 - 1 - p34 + 1) + p34;
    end
}
v_u_36.Expt = function(_, p37, p38, p39, p40) --[[ Name: Expt ]] --[[ Line: 9 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    if math.abs(p38 - p37) < 0.01 then
        return p38;
    else
        return p37 + (p38 - p37) * v_u_36:Expty(p37, p38, p39, p40);
    end;
end;
v_u_36.expt = function(_, p41, p42, p43, p44) --[[ Name: expt ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:Expt(p41, p42, p43, p44);
end;
v_u_36.BezierPt2ForT = function(_, p45, p46, p47, p48, p49, p50, p51, p52, p53) --[[ Name: BezierPt2ForT ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    v_u_36._BezierPt2ForT.X = v_u_36:BezierValForT(p45, p47, p49, p51, p53)
    v_u_36._BezierPt2ForT.Y = v_u_36:BezierValForT(p46, p48, p50, p52, p53)
    return v_u_36._BezierPt2ForT;
end;
v_u_36.BezierYForT = function(_, _, p54, _, p55, _, p56, _, p57, p58) --[[ Name: BezierYForT ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:BezierValForT(p54, p55, p56, p57, p58);
end;
v_u_36.YForPointOf2PtLine = function(_, p59, p60, p61) --[[ Name: YForPointOf2PtLine ]] --[[ Line: 72 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:YForPointOf2PtLineP1P2X(p59.X, p59.Y, p60.X, p60.Y, p61);
end;
v_u_36.sec_to_tick = function(_, p62) --[[ Name: sec_to_tick ]] --[[ Line: 96 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:SecondsToTick(p62);
end;
local v_u_63 = {}
v_u_36.NormalizedDefaultExptValueInSeconds = function(_, p64) --[[ Name: NormalizedDefaultExptValueInSeconds ]] --[[ Line: 105 ]]
    --[[ Upvalues: (copy 1): v_u_63, (copy 2): v_u_36 ]]
    if v_u_63[p64] == nil then
        v_u_63[p64] = v_u_36:ExptValueInSeconds(0.01, 1, p64)
    end;
    return v_u_63[p64];
end;
v_u_36.exptvsec = function(_, p65) --[[ Name: exptvsec ]] --[[ Line: 111 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:NormalizedDefaultExptValueInSeconds(p65);
end;
v_u_36.expt_sec = function(_, p66, p67, p68, p69) --[[ Name: expt_sec ]] --[[ Line: 114 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:Expt(p66, p67, v_u_36:exptvsec(p68), p69);
end;
v_u_36.incr_wrap = function(_, p70, p71, p72) --[[ Name: incr_wrap ]] --[[ Line: 124 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:IncrementWrap(p70, p71, p72);
end;
v_u_36.incr_clamp = function(_, p73, p74, p75, p76) --[[ Name: incr_clamp ]] --[[ Line: 139 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:IncrementClamp(p73, p74, p75, p76);
end;
v_u_36.move_to = function(_, p77, p78, p79, p80) --[[ Name: move_to ]] --[[ Line: 143 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    return v_u_36:IncrementClamp(p77, v_u_36:Sign(p78 - p77) * v_u_36:SecondsToTick(p79) * p80, 0, 1);
end;
return v_u_36;
