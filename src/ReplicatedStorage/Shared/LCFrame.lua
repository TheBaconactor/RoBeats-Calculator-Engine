-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.LVector3)
local v_u_16 = {
    ["__type"] = "LCFrame",
    ["TYPE_LCFRAME"] = "LCFrame",
    ["toWorldSpace"] = function(p2, p3) --[[ Name: toWorldSpace ]] --[[ Line: 579 ]]
        return p2 * p3;
    end,
    ["toObjectSpace"] = function(p4, p5) --[[ Name: toObjectSpace ]] --[[ Line: 587 ]]
        return p4:inverse() * p5;
    end,
    ["pointToWorldSpace"] = function(p6, p7) --[[ Name: pointToWorldSpace ]] --[[ Line: 591 ]]
        return p6 * p7;
    end,
    ["pointToObjectSpace"] = function(p8, p9) --[[ Name: pointToObjectSpace ]] --[[ Line: 595 ]]
        return p8:inverse() * p9;
    end,
    ["vectorToWorldSpace"] = function(p10, p11) --[[ Name: vectorToWorldSpace ]] --[[ Line: 599 ]]
        return (p10 - p10.p) * p11;
    end,
    ["vectorToObjectSpace"] = function(p12, p13) --[[ Name: vectorToObjectSpace ]] --[[ Line: 603 ]]
        return (p12 - p12.p):inverse() * p13;
    end,
    ["components"] = function(p14) --[[ Name: components ]] --[[ Line: 607 ]]
        local v15 = rawget(p14, "proxy")
        return v15.p.x, v15.p.y, v15.p.z, v15.m11, v15.m12, v15.m13, v15.m21, v15.m22, v15.m23, v15.m31, v15.m32, v15.m33;
    end
}
local v_u_90 = {
    ["__index"] = v_u_16,
    ["__newindex"] = function(p17, p18, p19) --[[ Name: __newindex ]] --[[ Line: 247 ]]
        if rawget(p17, "proxy")[p18] == nil then
            error(p18 .. " cannot be assigned to")
        else
            rawget(p17, "proxy")[p18] = p19
        end;
    end,
    ["__add"] = function(p20, p21) --[[ Name: __add ]] --[[ Line: 256 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_16 ]]
        local v22 = type(p20) == "table" and p20.__type
        if v22 then
            v22 = p20.__type == "LCFrame"
        end;
        local v23 = type(p21) == "table" and p21.__type
        if v23 then
            v23 = p21.__type == "LCFrame"
        end;
        local v24 = type(p21) == "table" and p21.__type
        if v24 then
            v24 = p21.__type == v_u_1.TYPE_LVECTOR3
        end;
        if v22 and v24 then
            local v25, v26, v27, v28, v29, v30, v31, v32, v33, v34, v35, v36 = p20:components()
            return v_u_16.new(v25 + p21.x, v26 + p21.y, v27 + p21.z, v28, v29, v30, v31, v32, v33, v34, v35, v36);
        elseif v23 then
            local v37 = type(p20)
            if v37 == "table" then
                v37 = p20.__type or v37
            end;
            error("bad argument #2 to \'?\' (CFrame expected, got " .. v37 .. ")")
        elseif v22 then
            local v38 = type(p21)
            if v38 == "table" then
                v38 = p21.__type or v38
            end;
            error("bad argument #2 to \'?\' (LVector3 expected, got " .. v38 .. ")")
        end;
    end,
    ["__sub"] = function(p39, p40) --[[ Name: __sub ]] --[[ Line: 275 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_16 ]]
        local v41 = type(p39) == "table" and p39.__type
        if v41 then
            v41 = p39.__type == "LCFrame"
        end;
        local v42 = type(p40) == "table" and p40.__type
        if v42 then
            v42 = p40.__type == "LCFrame"
        end;
        local v43 = type(p40) == "table" and p40.__type
        if v43 then
            v43 = p40.__type == v_u_1.TYPE_LVECTOR3
        end;
        if v41 and v43 then
            local v44, v45, v46, v47, v48, v49, v50, v51, v52, v53, v54, v55 = p39:components()
            return v_u_16.new(v44 - p40.x, v45 - p40.y, v46 - p40.z, v47, v48, v49, v50, v51, v52, v53, v54, v55);
        elseif v42 then
            local v56 = type(p39)
            if v56 == "table" then
                v56 = p39.__type or v56
            end;
            error("bad argument #2 to \'?\' (CFrame expected, got " .. v56 .. ")")
        elseif v41 then
            local v57 = type(p40)
            if v57 == "table" then
                v57 = p40.__type or v57
            end;
            error("bad argument #2 to \'?\' (LVector3 expected, got " .. v57 .. ")")
        end;
    end,
    ["__tostring"] = function(p58) --[[ Name: __tostring ]] --[[ Line: 314 ]]
        local v59 = { p58:components() }
        return ((((((((((("" .. "" .. v59[1] .. ", ") .. "" .. v59[2] .. ", ") .. "" .. v59[3] .. ", ") .. "\n" .. v59[4] .. ", ") .. "" .. v59[5] .. ", ") .. "" .. v59[6] .. ", ") .. "\n" .. v59[7] .. ", ") .. "" .. v59[8] .. ", ") .. "" .. v59[9] .. ", ") .. "\n" .. v59[10] .. ", ") .. "" .. v59[11] .. ", ") .. "" .. v59[12] .. "";
    end,
    ["set_components"] = function(p60, p61, p62, p63, p64, p65, p66, p67, p68, p69, p70, p71, p72) --[[ Name: set_components ]] --[[ Line: 337 ]]
        local v73 = rawget(p60, "proxy")
        p60.p:set(p61, p62, p63)
        v73.m11 = p64
        v73.m12 = p65
        v73.m13 = p66
        v73.m21 = p67
        v73.m22 = p68
        v73.m23 = p69
        v73.m31 = p70
        v73.m32 = p71
        v73.m33 = p72
        return p60;
    end,
    ["from_cframe"] = function(p74, p75) --[[ Name: from_cframe ]] --[[ Line: 346 ]]
        local v76, v77, v78, v79, v80, v81, v82, v83, v84, v85, v86, v87 = p75:components()
        p74:set_components(v76, v77, v78, v79, v80, v81, v82, v83, v84, v85, v86, v87)
        return p74;
    end,
    ["to_cframe"] = function(p88) --[[ Name: to_cframe ]] --[[ Line: 352 ]]
        local v89 = rawget(p88, "proxy")
        return CFrame.new(p88.p.x, p88.p.y, p88.p.z, v89.m11, v89.m12, v89.m13, v89.m21, v89.m22, v89.m23, v89.m31, v89.m32, v89.m33);
    end,
    ["__metatable"] = false
}
local l_max_0 = math.max
local l_cos_0 = math.cos
local l_sin_0 = math.sin
local l_acos_0 = math.acos
local l_asin_0 = math.asin
local l_sqrt_0 = math.sqrt
local l_atan2_0 = math.atan2
local v_u_91 = unpack
local v_u_92 = {
    ["m11"] = 1,
    ["m12"] = 0,
    ["m13"] = 0,
    ["m21"] = 0,
    ["m22"] = 1,
    ["m23"] = 0,
    ["m31"] = 0,
    ["m32"] = 0,
    ["m33"] = 1
}
local v_u_93 = v_u_1.new(1, 0, 0)
local v_u_94 = v_u_1.new(0, 1, 0)
local v_u_95 = v_u_1.new(0, 0, 1)
local function _(p96, p97, p98) --[[ Name: fromAxisAngle ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): l_cos_0, (copy 2): l_sin_0 ]]
    local l_unit_0 = p96.unit
    return p97 * l_cos_0(p98) + p97:Dot(l_unit_0) * l_unit_0 * (1 - l_cos_0(p98)) + l_unit_0:Cross(p97) * l_sin_0(p98);
end;
local function f_cfTimesv3(p99, p100) --[[ Name: cfTimesv3 ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local _, _, _, v101, v102, v103, v104, v105, v106, v107, v108, v109 = p99:components()
    return p99.p + p100.x * v_u_1.new(v101, v104, v107) + p100.y * v_u_1.new(v102, v105, v108) + p100.z * v_u_1.new(v103, v106, v109);
end;
local function f_fourByfour(p110, p111) --[[ Name: fourByfour ]] --[[ Line: 58 ]]
    --[[ Upvalues: (copy 1): v_u_91 ]]
    local v112, v113, v114, v115, v116, v117, v118, v119, v120, v121, v122, v123, v124, v125, v126, v127 = v_u_91(p110)
    local v128, v129, v130, v131, v132, v133, v134, v135, v136, v137, v138, v139, v140, v141, v142, v143 = v_u_91(p111)
    return v112 * v128 + v113 * v132 + v114 * v136 + v115 * v140, v112 * v129 + v113 * v133 + v114 * v137 + v115 * v141, v112 * v130 + v113 * v134 + v114 * v138 + v115 * v142, v112 * v131 + v113 * v135 + v114 * v139 + v115 * v143, v116 * v128 + v117 * v132 + v118 * v136 + v119 * v140, v116 * v129 + v117 * v133 + v118 * v137 + v119 * v141, v116 * v130 + v117 * v134 + v118 * v138 + v119 * v142, v116 * v131 + v117 * v135 + v118 * v139 + v119 * v143, v120 * v128 + v121 * v132 + v122 * v136 + v123 * v140, v120 * v129 + v121 * v133 + v122 * v137 + v123 * v141, v120 * v130 + v121 * v134 + v122 * v138 + v123 * v142, v120 * v131 + v121 * v135 + v122 * v139 + v123 * v143, v124 * v128 + v125 * v132 + v126 * v136 + v127 * v140, v124 * v129 + v125 * v133 + v126 * v137 + v127 * v141, v124 * v130 + v125 * v134 + v126 * v138 + v127 * v142, v124 * v131 + v125 * v135 + v126 * v139 + v127 * v143;
end;
local v_u_144 = {}
local v_u_145 = {}
local function f_cfTimescf_outcf(p146, p147, p148) --[[ Name: cfTimescf_outcf ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_144, (copy 2): v_u_145, (copy 3): f_fourByfour ]]
    local v149, v150, v151, v152, v153, v154, v155, v156, v157, v158, v159, v160 = p146:components()
    local v161, v162, v163, v164, v165, v166, v167, v168, v169, v170, v171, v172 = p147:components()
    v_u_144[1] = v152
    v_u_144[2] = v153
    v_u_144[3] = v154
    v_u_144[4] = v149
    v_u_144[5] = v155
    v_u_144[6] = v156
    v_u_144[7] = v157
    v_u_144[8] = v150
    v_u_144[9] = v158
    v_u_144[10] = v159
    v_u_144[11] = v160
    v_u_144[12] = v151
    v_u_144[13] = 0
    v_u_144[14] = 0
    v_u_144[15] = 0
    v_u_144[16] = 1
    v_u_145[1] = v164
    v_u_145[2] = v165
    v_u_145[3] = v166
    v_u_145[4] = v161
    v_u_145[5] = v167
    v_u_145[6] = v168
    v_u_145[7] = v169
    v_u_145[8] = v162
    v_u_145[9] = v170
    v_u_145[10] = v171
    v_u_145[11] = v172
    v_u_145[12] = v163
    v_u_145[13] = 0
    v_u_145[14] = 0
    v_u_145[15] = 0
    v_u_145[16] = 1
    local v173, v174, v175, v176, v177, v178, v179, v180, v181, v182, v183, v184, _, _, _, _ = f_fourByfour(v_u_144, v_u_145)
    return p148:set_components(v176, v180, v184, v173, v174, v175, v177, v178, v179, v181, v182, v183);
end;
local function f_cfTimescf(p185, p186) --[[ Name: cfTimescf ]] --[[ Line: 129 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): f_cfTimescf_outcf ]]
    return f_cfTimescf_outcf(p185, p186, (v_u_16.new()));
end;
local function f_getDeterminant(p187) --[[ Name: getDeterminant ]] --[[ Line: 134 ]]
    local v188, v189, v190, v191, v192, v193, v194, v195, v196, v197, v198, v199 = p187:components()
    return v191 * v195 * v199 * 1 + v191 * v196 * v190 * 0 + v191 * v189 * v198 * 0 + v192 * v194 * v190 * 0 + v192 * v196 * v197 * 1 + v192 * v189 * v199 * 0 + v193 * v194 * v198 * 1 + v193 * v195 * v190 * 0 + v193 * v189 * v197 * 0 + v188 * v194 * v199 * 0 + v188 * v195 * v197 * 0 + v188 * v196 * v198 * 0 - v191 * v195 * v190 * 0 - v191 * v196 * v198 * 1 - v191 * v189 * v199 * 0 - v192 * v194 * v199 * 1 - v192 * v196 * v190 * 0 - v192 * v189 * v197 * 0 - v193 * v194 * v190 * 0 - v193 * v195 * v197 * 1 - v193 * v189 * v198 * 0 - v188 * v194 * v198 * 0 - v188 * v195 * v199 * 0 - v188 * v196 * v197 * 0;
end;
local function f_invert4x4(p200) --[[ Name: invert4x4 ]] --[[ Line: 148 ]]
    --[[ Upvalues: (copy 1): f_getDeterminant, (copy 2): v_u_16 ]]
    local v201, v202, v203, v204, v205, v206, v207, v208, v209, v210, v211, v212 = p200:components()
    local v213 = f_getDeterminant(p200)
    if v213 == 0 then
        return p200;
    else
        return v_u_16.new((v205 * v202 * v212 + v206 * v208 * v203 + v201 * v209 * v211 - v205 * v209 * v203 - v206 * v202 * v211 - v201 * v208 * v212) / v213, (v204 * v209 * v203 + v206 * v202 * v210 + v201 * v207 * v212 - v204 * v202 * v212 - v206 * v207 * v203 - v201 * v209 * v210) / v213, (v204 * v202 * v211 + v205 * v207 * v203 + v201 * v208 * v210 - v204 * v208 * v203 - v205 * v202 * v210 - v201 * v207 * v211) / v213, (v208 * v212 * 1 + v209 * v203 * 0 + v202 * v211 * 0 - v208 * v203 * 0 - v209 * v211 * 1 - v202 * v212 * 0) / v213, (v205 * v203 * 0 + v206 * v211 * 1 + v201 * v212 * 0 - v205 * v212 * 1 - v206 * v203 * 0 - v201 * v211 * 0) / v213, (v205 * v209 * 1 + v206 * v202 * 0 + v201 * v208 * 0 - v205 * v202 * 0 - v206 * v208 * 1 - v201 * v209 * 0) / v213, (v207 * v203 * 0 + v209 * v210 * 1 + v202 * v212 * 0 - v207 * v212 * 1 - v209 * v203 * 0 - v202 * v210 * 0) / v213, (v204 * v212 * 1 + v206 * v203 * 0 + v201 * v210 * 0 - v204 * v203 * 0 - v206 * v210 * 1 - v201 * v212 * 0) / v213, (v204 * v202 * 0 + v206 * v207 * 1 + v201 * v209 * 0 - v204 * v209 * 1 - v206 * v202 * 0 - v201 * v207 * 0) / v213, (v207 * v211 * 1 + v208 * v203 * 0 + v202 * v210 * 0 - v207 * v203 * 0 - v208 * v210 * 1 - v202 * v211 * 0) / v213, (v204 * v203 * 0 + v205 * v210 * 1 + v201 * v211 * 0 - v204 * v211 * 1 - v205 * v203 * 0 - v201 * v210 * 0) / v213, (v204 * v208 * 1 + v205 * v202 * 0 + v201 * v207 * 0 - v204 * v202 * 0 - v205 * v207 * 1 - v201 * v208 * 0) / v213);
    end;
end;
local function f_quaternionToMatrix(p214, p215, p216, p217) --[[ Name: quaternionToMatrix ]] --[[ Line: 175 ]]
    return {
        0,
        0,
        0,
        1 - 2 * p215 ^ 2 - 2 * p216 ^ 2,
        2 * (p214 * p215 - p216 * p217),
        2 * (p214 * p216 + p215 * p217),
        2 * (p214 * p215 + p216 * p217),
        1 - 2 * p214 ^ 2 - 2 * p216 ^ 2,
        2 * (p215 * p216 - p214 * p217),
        2 * (p214 * p216 - p215 * p217),
        2 * (p215 * p216 + p214 * p217),
        1 - 2 * p214 ^ 2 - 2 * p215 ^ 2
    };
end;
local function f_quaternionFromCFrame(p218) --[[ Name: quaternionFromCFrame ]] --[[ Line: 188 ]]
    --[[ Upvalues: (copy 1): l_sqrt_0, (copy 2): v_u_1, (copy 3): l_max_0 ]]
    local _, _, _, v219, v220, v221, v222, v223, v224, v225, v226, v227 = p218:components()
    local v228 = v219 + v223 + v227
    if v228 > 0 then
        local v229 = l_sqrt_0(1 + v228)
        local v230 = 0.5 / v229
        return v229 * 0.5, v_u_1.new((v226 - v224) * v230, (v221 - v225) * v230, (v222 - v220) * v230);
    end;
    local v231 = l_max_0(v219, v223, v227)
    if v231 == v219 then
        local v232 = l_sqrt_0(1 + v219 - v223 - v227)
        local v233 = 0.5 / v232
        return (v226 - v224) * v233, v_u_1.new(v232 * 0.5, (v222 + v220) * v233, (v221 + v225) * v233);
    end;
    if v231 == v223 then
        local v234 = l_sqrt_0(1 - v219 + v223 - v227)
        local v235 = 0.5 / v234
        return (v221 - v225) * v235, v_u_1.new((v222 + v220) * v235, v234 * 0.5, (v226 + v224) * v235);
    end;
    if v231 == v227 then
        local v236 = l_sqrt_0(1 - v219 - v223 + v227)
        local v237 = 0.5 / v236
        return (v222 - v220) * v237, v_u_1.new((v221 + v225) * v237, (v226 + v224) * v237, v236 * 0.5);
    end;
end;
local function f_lerp(p238, p239, p240) --[[ Name: lerp ]] --[[ Line: 214 ]]
    --[[ Upvalues: (copy 1): f_quaternionFromCFrame, (copy 2): l_acos_0, (copy 3): v_u_16 ]]
    local v241, v242 = f_quaternionFromCFrame(p238:inverse() * p239)
    local v243 = l_acos_0(v241) * 2
    local v244 = p238.p:Lerp(p239.p, p240)
    if v243 == 0 then
        local _, _, _, v245, v246, v247, v248, v249, v250, v251, v252, v253 = p238:components()
        return v_u_16.new(v244.x, v244.y, v244.z, v245, v246, v247, v248, v249, v250, v251, v252, v253);
    else
        local _, _, _, v254, v255, v256, v257, v258, v259, v260, v261, v262 = (p238 * v_u_16.fromAxisAngle(v242, v243 * p240)):components()
        return v_u_16.new(v244.x, v244.y, v244.z, v254, v255, v256, v257, v258, v259, v260, v261, v262);
    end;
end;
v_u_90.__index = function(p263, p264) --[[ Name: __index ]] --[[ Line: 233 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_90 ]]
    if p264 == "x" or (p264 == "y" or p264 == "z") then
        return rawget(p263, "proxy").p[p264];
    end;
    if p264 == "p" or p264 == "lookVector" then
        return rawget(p263, "proxy")[p264];
    end;
    if v_u_16[p264] then
        return v_u_16[p264];
    end;
    if typeof((rawget(v_u_90, p264))) == "function" then
        return rawget(v_u_90, p264);
    end;
    error(p264 .. " is not a valid member of CFrame")
end;
v_u_90.__mul = function(p265, p266) --[[ Name: __mul ]] --[[ Line: 294 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): f_cfTimesv3, (copy 3): f_cfTimescf ]]
    local v267 = type(p265) == "table" and p265.__type
    if v267 then
        v267 = p265.__type == "LCFrame"
    end;
    local v268 = type(p266) == "table" and p266.__type
    if v268 then
        v268 = p266.__type == "LCFrame"
    end;
    local v269 = type(p266) == "table" and p266.__type
    if v269 then
        v269 = p266.__type == v_u_1.TYPE_LVECTOR3
    end;
    if v267 and v269 then
        return f_cfTimesv3(p265, p266);
    elseif v267 and v268 then
        return f_cfTimescf(p265, p266);
    elseif v267 then
        local v270 = type(p265)
        if v270 == "table" then
            v270 = p265.__type or v270
        end;
        error("bad argument #2 to \'?\' (LVector expected, got " .. v270 .. " )")
    elseif v268 then
        local v271 = type(p265)
        if v271 == "table" then
            v271 = p265.__type or v271
        end;
        error("bad argument #1 to \'?\' (CFrame expected, got " .. v271 .. " )")
    end;
end;
v_u_90.set_identity = function(p272) --[[ Name: set_identity ]] --[[ Line: 328 ]]
    --[[ Upvalues: (copy 1): v_u_92 ]]
    p272.p:set(0, 0, 0)
    local v273 = rawget(p272, "proxy")
    for v274, v275 in next, v_u_92 do
        v273[v274] = v275
    end;
    return p272;
end;
v_u_90.store_mul_result = function(p276, p277, p278) --[[ Name: store_mul_result ]] --[[ Line: 362 ]]
    --[[ Upvalues: (copy 1): f_cfTimescf_outcf ]]
    return f_cfTimescf_outcf(p277, p278, p276);
end;
v_u_90.set_angles = function(p279, p280, p281, p282) --[[ Name: set_angles ]] --[[ Line: 366 ]]
    --[[ Upvalues: (copy 1): l_cos_0, (copy 2): l_sin_0 ]]
    return p279:set_components(0, 0, 0, l_cos_0(p281) * l_cos_0(p282), -l_cos_0(p281) * l_sin_0(p282), l_sin_0(p281), l_cos_0(p282) * l_sin_0(p280) * l_sin_0(p281) + l_cos_0(p280) * l_sin_0(p282), l_cos_0(p280) * l_cos_0(p282) - l_sin_0(p280) * l_sin_0(p281) * l_sin_0(p282), -l_cos_0(p281) * l_sin_0(p280), l_sin_0(p280) * l_sin_0(p282) - l_cos_0(p280) * l_cos_0(p282) * l_sin_0(p281), l_cos_0(p282) * l_sin_0(p280) + l_cos_0(p280) * l_sin_0(p281) * l_sin_0(p282), l_cos_0(p280) * l_cos_0(p281));
end;
local v_u_283 = v_u_1.new()
local v_u_284 = v_u_1.new()
local v_u_285 = v_u_1.new()
v_u_90.set_eye_look = function(p286, p287, p288) --[[ Name: set_eye_look ]] --[[ Line: 383 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_283, (copy 3): v_u_284, (copy 4): v_u_94, (copy 5): v_u_285 ]]
    local v289 = type(p287) == "table" and p287.__type
    if v289 then
        v289 = p287.__type == v_u_1.TYPE_LVECTOR3
    end;
    local v290 = type(p288) == "table" and p288.__type
    if v290 then
        v290 = p288.__type == v_u_1.TYPE_LVECTOR3
    end;
    if not (v289 or v290) then
        local v291 = type(p287)
        if v291 == "table" then
            v291 = p287.__type or v291
        end;
        error("bad argument #1 to \'new\' (LVector3 expected, got" .. v291 .. ")")
    end;
    v_u_283:store_sub_result(p287, p288)
    v_u_283:store_normalized(v_u_283)
    v_u_284:store_cross_result(v_u_94, v_u_283)
    v_u_284:store_normalized(v_u_284)
    v_u_285:store_cross_result(v_u_283, v_u_284)
    v_u_285:store_normalized(v_u_285)
    if v_u_284.magnitude == 0 then
        if v_u_283.y < 0 then
            v_u_284:set(0, 0, -1)
            v_u_285:set(1, 0, 0)
            v_u_283:set(0, -1, 0)
        else
            v_u_284:set(0, 0, 1)
            v_u_285:set(1, 0, 0)
            v_u_283:set(0, 1, 0)
        end;
    end;
    local v292 = rawget(p286, "proxy")
    v292.p:set(p287.x, p287.y, p287.z)
    local l_x_0 = v_u_284.x
    local l_x_1 = v_u_285.x
    local l_x_2 = v_u_283.x
    v292.m11 = l_x_0
    v292.m12 = l_x_1
    v292.m13 = l_x_2
    local l_y_0 = v_u_284.y
    local l_y_1 = v_u_285.y
    local l_y_2 = v_u_283.y
    v292.m21 = l_y_0
    v292.m22 = l_y_1
    v292.m23 = l_y_2
    local l_z_0 = v_u_284.z
    local l_z_1 = v_u_285.z
    local l_z_2 = v_u_283.z
    v292.m31 = l_z_0
    v292.m32 = l_z_1
    v292.m33 = l_z_2
    return p286;
end;
v_u_16.new = function(...) --[[ Name: new ]] --[[ Line: 426 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_92, (copy 3): v_u_94, (copy 4): f_quaternionToMatrix, (copy 5): v_u_90 ]]
    local v293 = {
        ["proxy"] = {}
    }
    v293.proxy.p = v_u_1.new(0, 0, 0)
    for v294, v295 in next, v_u_92 do
        v293.proxy[v294] = v295
    end;
    local v296 = { ... }
    local v297 = #v296
    if v297 > 12 then
        error("Invalid number of arguments: " .. v297)
    elseif v297 == 1 then
        local v298 = v296[1]
        local v299 = type(v298) == "table" and v298.__type
        if v299 then
            v299 = v298.__type == v_u_1.TYPE_LVECTOR3
        end;
        if not v299 then
            local v300 = type(v298)
            if v300 == "table" then
                v300 = v298.__type or v300
            end;
            error("bad argument #1 to \'new\' (LVector3 expected, got" .. v300 .. ")")
        end;
        v293.proxy.p = v_u_1.new(v298.x, v298.y, v298.z)
    elseif v297 == 2 then
        local v301 = v296[1]
        local v302 = v296[2]
        local v303 = type(v301) == "table" and v301.__type
        if v303 then
            v303 = v301.__type == v_u_1.TYPE_LVECTOR3
        end;
        local v304 = type(v302) == "table" and v302.__type
        if v304 then
            v304 = v302.__type == v_u_1.TYPE_LVECTOR3
        end;
        if not (v303 or v304) then
            local v305 = type(v301)
            if v305 == "table" then
                v305 = v301.__type or v305
            end;
            error("bad argument #1 to \'new\' (LVector3 expected, got" .. v305 .. ")")
        end;
        local l_unit_1 = (v301 - v302).unit
        local l_unit_2 = v_u_94:Cross(l_unit_1).unit
        local l_unit_3 = l_unit_1:Cross(l_unit_2).unit
        if l_unit_2.magnitude == 0 then
            if l_unit_1.y < 0 then
                l_unit_2 = v_u_1.new(0, 0, -1)
                l_unit_3 = v_u_1.new(1, 0, 0)
                l_unit_1 = v_u_1.new(0, -1, 0)
            else
                l_unit_2 = v_u_1.new(0, 0, 1)
                l_unit_3 = v_u_1.new(1, 0, 0)
                l_unit_1 = v_u_1.new(0, 1, 0)
            end;
        end;
        v293.proxy.p = v_u_1.new(v301.x, v301.y, v301.z)
        local l_proxy_0 = v293.proxy
        local l_proxy_1 = v293.proxy
        local l_proxy_2 = v293.proxy
        local l_x_3 = l_unit_2.x
        local l_x_4 = l_unit_3.x
        local l_x_5 = l_unit_1.x
        l_proxy_0.m11 = l_x_3
        l_proxy_1.m12 = l_x_4
        l_proxy_2.m13 = l_x_5
        local l_proxy_3 = v293.proxy
        local l_proxy_4 = v293.proxy
        local l_proxy_5 = v293.proxy
        local l_y_3 = l_unit_2.y
        local l_y_4 = l_unit_3.y
        local l_y_5 = l_unit_1.y
        l_proxy_3.m21 = l_y_3
        l_proxy_4.m22 = l_y_4
        l_proxy_5.m23 = l_y_5
        local l_proxy_6 = v293.proxy
        local l_proxy_7 = v293.proxy
        local l_proxy_8 = v293.proxy
        local l_z_3 = l_unit_2.z
        local l_z_4 = l_unit_3.z
        local l_z_5 = l_unit_1.z
        l_proxy_6.m31 = l_z_3
        l_proxy_7.m32 = l_z_4
        l_proxy_8.m33 = l_z_5
    elseif v297 == 3 then
        for v306 = 1, v297 do
            local v307 = type(v296[v306])
            if v307 ~= "number" then
                error("bad argument #" .. v306 .. " to \'new\' (Number expected, got " .. v307 .. ")")
            end;
        end;
        v293.proxy.p = v_u_1.new(v296[1], v296[2], v296[3])
    elseif v297 == 7 then
        for v308 = 1, v297 do
            local v309 = type(v296[v308])
            if v309 ~= "number" then
                error("bad argument #" .. v308 .. " to \'new\' (Number expected, got " .. v309 .. ")")
            end;
        end;
        local v310 = f_quaternionToMatrix(v296[4], v296[5], v296[6], v296[7])
        v293.proxy.p = v_u_1.new(v296[1], v296[2], v296[3])
        local l_proxy_9 = v293.proxy
        local l_proxy_10 = v293.proxy
        local l_proxy_11 = v293.proxy
        local v311 = v310[4]
        local v312 = v310[5]
        local v313 = v310[6]
        l_proxy_9.m11 = v311
        l_proxy_10.m12 = v312
        l_proxy_11.m13 = v313
        local l_proxy_12 = v293.proxy
        local l_proxy_13 = v293.proxy
        local l_proxy_14 = v293.proxy
        local v314 = v310[7]
        local v315 = v310[8]
        local v316 = v310[9]
        l_proxy_12.m21 = v314
        l_proxy_13.m22 = v315
        l_proxy_14.m23 = v316
        local l_proxy_15 = v293.proxy
        local l_proxy_16 = v293.proxy
        local l_proxy_17 = v293.proxy
        local v317 = v310[10]
        local v318 = v310[11]
        local v319 = v310[12]
        l_proxy_15.m31 = v317
        l_proxy_16.m32 = v318
        l_proxy_17.m33 = v319
    elseif v297 == 12 then
        for v320 = 1, v297 do
            local v321 = type(v296[v320])
            if v321 ~= "number" then
                error("bad argument #" .. v320 .. " to \'new\' (Number expected, got " .. v321 .. ")")
            end;
        end;
        v293.proxy.p = v_u_1.new(v296[1], v296[2], v296[3])
        local l_proxy_18 = v293.proxy
        local l_proxy_19 = v293.proxy
        local l_proxy_20 = v293.proxy
        local v322 = v296[4]
        local v323 = v296[5]
        local v324 = v296[6]
        l_proxy_18.m11 = v322
        l_proxy_19.m12 = v323
        l_proxy_20.m13 = v324
        local l_proxy_21 = v293.proxy
        local l_proxy_22 = v293.proxy
        local l_proxy_23 = v293.proxy
        local v325 = v296[7]
        local v326 = v296[8]
        local v327 = v296[9]
        l_proxy_21.m21 = v325
        l_proxy_22.m22 = v326
        l_proxy_23.m23 = v327
        local l_proxy_24 = v293.proxy
        local l_proxy_25 = v293.proxy
        local l_proxy_26 = v293.proxy
        local v328 = v296[10]
        local v329 = v296[11]
        local v330 = v296[12]
        l_proxy_24.m31 = v328
        l_proxy_25.m32 = v329
        l_proxy_26.m33 = v330
    elseif v297 > 0 then
        for v331 = 1, v297 do
            local v332 = type(v296[v331])
            if v332 ~= "number" then
                error("bad argument #" .. v331 .. " to \'new\' (Number expected, got " .. v332 .. ")")
            end;
        end;
        error("bad argument #" .. v297 + 1 .. " to \'new\' (Number expected, got nil)")
    end;
    v293.proxy.lookVector = v_u_1.new(-v293.proxy.m13, -v293.proxy.m23, -v293.proxy.m33)
    return setmetatable(v293, v_u_90);
end;
v_u_16.fromAxisAngle = function(p333, p334) --[[ Name: fromAxisAngle ]] --[[ Line: 525 ]]
    --[[ Upvalues: (copy 1): v_u_93, (copy 2): l_cos_0, (copy 3): l_sin_0, (copy 4): v_u_94, (copy 5): v_u_95, (copy 6): v_u_16 ]]
    local l_unit_4 = p333.unit
    local v335 = v_u_93
    local l_unit_5 = l_unit_4.unit
    local v336 = v335 * l_cos_0(p334) + v335:Dot(l_unit_5) * l_unit_5 * (1 - l_cos_0(p334)) + l_unit_5:Cross(v335) * l_sin_0(p334)
    local v337 = v_u_94
    local l_unit_6 = l_unit_4.unit
    local v338 = v337 * l_cos_0(p334) + v337:Dot(l_unit_6) * l_unit_6 * (1 - l_cos_0(p334)) + l_unit_6:Cross(v337) * l_sin_0(p334)
    local v339 = v_u_95
    local l_unit_7 = l_unit_4.unit
    local v340 = v339 * l_cos_0(p334) + v339:Dot(l_unit_7) * l_unit_7 * (1 - l_cos_0(p334)) + l_unit_7:Cross(v339) * l_sin_0(p334)
    return v_u_16.new(0, 0, 0, v336.x, v338.x, v340.x, v336.y, v338.y, v340.y, v336.z, v338.z, v340.z);
end;
v_u_16.Angles = function(p341, p342, p343) --[[ Name: Angles ]] --[[ Line: 538 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_93, (copy 3): v_u_94, (copy 4): v_u_95 ]]
    return v_u_16.fromAxisAngle(v_u_93, p341) * v_u_16.fromAxisAngle(v_u_94, p342) * v_u_16.fromAxisAngle(v_u_95, p343);
end;
v_u_16.fromEulerAnglesXYZ = function(p344, p345, p346) --[[ Name: fromEulerAnglesXYZ ]] --[[ Line: 567 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    return v_u_16.Angles(p344, p345, p346);
end;
v_u_16.inverse = function(p347) --[[ Name: inverse ]] --[[ Line: 571 ]]
    --[[ Upvalues: (copy 1): f_invert4x4 ]]
    return f_invert4x4(p347);
end;
v_u_16.lerp = function(p348, p349, p350) --[[ Name: lerp ]] --[[ Line: 575 ]]
    --[[ Upvalues: (copy 1): f_lerp ]]
    return f_lerp(p348, p349, p350);
end;
v_u_16.toWorldSpace = function(p351, p352) --[[ Name: toWorldSpace ]] --[[ Line: 583 ]]
    return p351 * p352;
end;
v_u_16.toEulerAnglesXYZ = function(p353) --[[ Name: toEulerAnglesXYZ ]] --[[ Line: 612 ]]
    --[[ Upvalues: (copy 1): l_atan2_0, (copy 2): l_asin_0 ]]
    local _, _, _, v354, v355, v356, _, _, v357, _, _, v358 = p353:components()
    return l_atan2_0(-v357, v358), l_asin_0(v356), l_atan2_0(-v355, v354);
end;
return v_u_16;
