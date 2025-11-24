-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:04 PM
-- Cached decompilation

local v_u_16 = {
    ["_TYPE"] = "module",
    ["_NAME"] = "matrix",
    ["_VERSION"] = "0.2.11.20120416",
    ["type"] = function(p1) --[[ Name: type ]] --[[ Line: 714 ]]
        local v2 = p1[1][1]
        return type(v2) ~= "table" and "number" or (not v2.type and "tensor" or v2:type());
    end,
    ["rows"] = function(p3) --[[ Name: rows ]] --[[ Line: 925 ]]
        return #p3;
    end,
    ["columns"] = function(p4) --[[ Name: columns ]] --[[ Line: 931 ]]
        return #p4[1];
    end,
    ["getelement"] = function(p5, p6, p7) --[[ Name: getelement ]] --[[ Line: 947 ]]
        if p5[p6] and p5[p6][p7] then
            return p5[p6][p7];
        end;
    end,
    ["ipairs"] = function(p8) --[[ Name: ipairs ]] --[[ Line: 966 ]]
        local v_u_9 = 1
        local v_u_10 = 0
        local v_u_11 = #p8
        local v_u_12 = #p8[1]
        return function() --[[ Name: iter ]] --[[ Line: 968 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_12, (ref 3): v_u_9, (copy 4): v_u_11 ]]
            v_u_10 = v_u_10 + 1
            if v_u_12 < v_u_10 then
                v_u_9 = v_u_9 + 1
                v_u_10 = 1
            end;
            if v_u_9 <= v_u_11 then
                return v_u_9, v_u_10;
            end;
        end;
    end,
    ["scalar"] = function(p13, p14) --[[ Name: scalar ]] --[[ Line: 989 ]]
        return p13[1][1] * p14[1][1] + p13[2][1] * p14[2][1] + p13[3][1] * p14[3][1];
    end,
    ["len"] = function(p15) --[[ Name: len ]] --[[ Line: 1005 ]]
        return math.sqrt(p15[1][1] ^ 2 + p15[2][1] ^ 2 + p15[3][1] ^ 2);
    end
}
local v_u_22 = {
    ["__add"] = function(...) --[[ Line: 1060 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.add(...);
    end,
    ["__sub"] = function(...) --[[ Line: 1065 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.sub(...);
    end,
    ["__unm"] = function(p17) --[[ Line: 1090 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.mulnum(p17, -1);
    end,
    ["__eq"] = function(p18, p19) --[[ Line: 1111 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        if v_u_16.type(p18) ~= v_u_16.type(p19) then
            return false;
        end;
        if #p18 ~= #p19 or #p18[1] ~= #p19[1] then
            return false;
        end;
        for v20 = 1, #p18 do
            for v21 = 1, #p18[1] do
                if p18[v20][v21] ~= p19[v20][v21] then
                    return false;
                end;
            end;
        end;
        return true;
    end,
    ["__tostring"] = function(...) --[[ Line: 1132 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.tostring(...);
    end,
    ["__call"] = function(...) --[[ Line: 1137 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        v_u_16.print(...)
    end,
    ["__index"] = {}
}
v_u_16.new = function(_, p23, p24, p25) --[[ Name: new ]] --[[ Line: 132 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    if type(p23) == "table" then
        if type(p23[1]) == "table" then
            return setmetatable(p23, v_u_22);
        else
            return setmetatable({
                { p23[1] },
                { p23[2] },
                { p23[3] }
            }, v_u_22);
        end;
    else
        local v26 = {}
        local v27 = p25 or 0
        if p24 == "I" then
            for v28 = 1, p23 do
                v26[v28] = {}
                for v29 = 1, p23 do
                    if v28 == v29 then
                        v26[v28][v29] = 1
                    else
                        v26[v28][v29] = 0
                    end;
                end;
            end;
        else
            for v30 = 1, p23 do
                v26[v30] = {}
                for v31 = 1, p24 do
                    v26[v30][v31] = v27
                end;
            end;
        end;
        return setmetatable(v26, v_u_22);
    end;
end;
setmetatable(v_u_16, {
    ["__call"] = function(...) --[[ Name: __call ]] --[[ Line: 172 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.new(...);
    end
})
v_u_16.add = function(p32, p33) --[[ Name: add ]] --[[ Line: 194 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    local v34 = {}
    for v35 = 1, #p32 do
        local v36 = {}
        v34[v35] = v36
        for v37 = 1, #p32[1] do
            v36[v37] = p32[v35][v37] + p33[v35][v37]
        end;
    end;
    return setmetatable(v34, v_u_22);
end;
v_u_16.sub = function(p38, p39) --[[ Name: sub ]] --[[ Line: 208 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    local v40 = {}
    for v41 = 1, #p38 do
        local v42 = {}
        v40[v41] = v42
        for v43 = 1, #p38[1] do
            v42[v43] = p38[v41][v43] - p39[v41][v43]
        end;
    end;
    return setmetatable(v40, v_u_22);
end;
v_u_16.mul = function(p44, p45) --[[ Name: mul ]] --[[ Line: 223 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    local v46 = {}
    for v47 = 1, #p44 do
        v46[v47] = {}
        for v48 = 1, #p45[1] do
            local v49 = p44[v47][1] * p45[1][v48]
            for v50 = 2, #p44[1] do
                v49 = v49 + p44[v47][v50] * p45[v50][v48]
            end;
            v46[v47][v48] = v49
        end;
    end;
    return setmetatable(v46, v_u_22);
end;
v_u_16.div = function(p51, p52) --[[ Name: div ]] --[[ Line: 244 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    local v53, v54 = v_u_16.invert(p52)
    if v53 then
        return v_u_16.mul(p51, v53);
    else
        return v53, v54;
    end;
end;
v_u_16.mulnum = function(p55, p56) --[[ Name: mulnum ]] --[[ Line: 254 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    local v57 = {}
    for v58 = 1, #p55 do
        v57[v58] = {}
        for v59 = 1, #p55[1] do
            v57[v58][v59] = p55[v58][v59] * p56
        end;
    end;
    return setmetatable(v57, v_u_22);
end;
v_u_16.divnum = function(p60, p61) --[[ Name: divnum ]] --[[ Line: 270 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    local v62 = {}
    for v63 = 1, #p60 do
        local v64 = {}
        v62[v63] = v64
        for v65 = 1, #p60[1] do
            v64[v65] = p60[v63][v65] / p61
        end;
    end;
    return setmetatable(v62, v_u_22);
end;
v_u_16.pow = function(p66, p67) --[[ Name: pow ]] --[[ Line: 292 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    assert(p67 == math.floor(p67), "exponent not an integer")
    if p67 == 0 then
        return v_u_16:new(#p66, "I");
    end;
    if p67 < 0 then
        local v68
        p66, v68 = v_u_16.invert(p66)
        if not p66 then
            return p66, v68;
        end;
        p67 = -p67
    end;
    local v69 = v_u_16.copy(p66)
    for _ = 2, p67 do
        v69 = v_u_16.mul(v69, p66)
    end;
    return v69;
end;
local function f_number_norm2(p70) --[[ Name: number_norm2 ]] --[[ Line: 309 ]]
    return p70 * p70;
end;
v_u_16.det = function(p71) --[[ Name: det ]] --[[ Line: 323 ]]
    --[[ Upvalues: (copy 1): f_number_norm2, (copy 2): v_u_16 ]]
    assert(#p71 == #p71[1], "matrix not square")
    local v72 = #p71
    if v72 == 1 then
        return p71[1][1];
    end;
    if v72 == 2 then
        return p71[1][1] * p71[2][2] - p71[2][1] * p71[1][2];
    end;
    if v72 == 3 then
        return p71[1][1] * p71[2][2] * p71[3][3] + p71[1][2] * p71[2][3] * p71[3][1] + p71[1][3] * p71[2][1] * p71[3][2] - p71[1][3] * p71[2][2] * p71[3][1] - p71[1][1] * p71[2][3] * p71[3][2] - p71[1][2] * p71[2][1] * p71[3][3];
    end;
    local v73 = p71[1][1]
    local v74 = type(v73) == "table" and (v73.zero or 0) or 0
    local v75 = type(v73) == "table" and v73.norm2 or f_number_norm2
    local v76 = v_u_16.copy(p71)
    local v77 = 1
    for v78 = 1, #v76[1] do
        local v79 = #v76
        local v80 = nil
        local v81 = nil
        for v82 = 1, v79 do
            local v83 = v76[v82][v78]
            if v80 then
                if v83 ~= v74 and math.abs(v75(v83) - 1) < math.abs(v75(v80) - 1) then
                    v81 = v82
                    v80 = v83
                end;
            elseif v83 ~= v74 then
                v81 = v82
                v80 = v83
            end;
        end;
        if not v80 then
            return v77 * 0;
        end;
        if v81 ~= v79 then
            local v84 = v76[v81]
            local v85 = v76[v79]
            v76[v79] = v84
            v76[v81] = v85
            v77 = -v77
        end;
        for v86 = 1, v79 - 1 do
            if v76[v86][v78] ~= v74 then
                local v87 = v76[v86][v78] / v80
                for v88 = v78 + 1, #v76[1] do
                    v76[v86][v88] = v76[v86][v88] - v87 * v76[v79][v88]
                end;
            end;
        end;
        if math.fmod(v79, 2) == 0 then
            v77 = -v77
        end;
        v77 = v77 * v80
        table.remove(v76)
    end;
    return v77;
end;
local function v_u_99(p89, p90, p91, p92) --[[ Line: 422 ]]
    local v93 = (1 / 0)
    local v94 = nil
    for v95 = p90, #p89 do
        local v96 = math.abs((p92(p89[v95][p91])))
        if v96 > 0 and v96 < v93 then
            v94 = v95
            v93 = v96
        end;
    end;
    if not v94 then
        return false;
    end;
    if v94 ~= p90 then
        local v97 = p89[v94]
        local v98 = p89[p90]
        p89[p90] = v97
        p89[v94] = v98
    end;
    return true;
end;
local function _(p100) --[[ Name: copy ]] --[[ Line: 444 ]]
    if type(p100) == "table" then
        p100 = p100.copy(p100) or p100
    end;
    return p100;
end;
v_u_16.dogauss = function(p101) --[[ Name: dogauss ]] --[[ Line: 450 ]]
    --[[ Upvalues: (copy 1): f_number_norm2, (copy 2): v_u_99 ]]
    local v102 = p101[1][1]
    local v103 = type(v102) == "table" and (v102.zero or 0) or 0
    local v104 = type(v102) == "table" and (v102.one or 1) or 1
    local v105 = type(v102) == "table" and v102.norm2 or f_number_norm2
    local v106 = #p101
    local v107 = #p101[1]
    for v108 = 1, v106 do
        if not v_u_99(p101, v108, v108, v105) then
            return false, v108 - 1;
        end;
        for v109 = v108 + 1, v106 do
            if p101[v109][v108] ~= v103 then
                local v110 = p101[v109][v108] / p101[v108][v108]
                local v111 = p101[v109]
                local v112
                if type(v103) == "table" then
                    v112 = v103.copy(v103) or v103
                else
                    v112 = v103
                end;
                v111[v108] = v112
                for v113 = v108 + 1, v107 do
                    p101[v109][v113] = p101[v109][v113] - v110 * p101[v108][v113]
                end;
            end;
        end;
    end;
    for v114 = v106, 1, -1 do
        local v115 = p101[v114][v114]
        for v116 = v114 + 1, v107 do
            p101[v114][v116] = p101[v114][v116] / v115
        end;
        for v117 = v114 - 1, 1, -1 do
            if p101[v117][v114] ~= v103 then
                local v118 = p101[v117][v114]
                for v119 = v114 + 1, v107 do
                    p101[v117][v119] = p101[v117][v119] - v118 * p101[v114][v119]
                end;
                local v120 = p101[v117]
                local v121
                if type(v103) == "table" then
                    v121 = v103.copy(v103) or v103
                else
                    v121 = v103
                end;
                v120[v114] = v121
            end;
        end;
        local v122 = p101[v114]
        local v123
        if type(v104) == "table" then
            v123 = v104.copy(v104) or v104
        else
            v123 = v104
        end;
        v122[v114] = v123
    end;
    return true;
end;
v_u_16.invert = function(p124) --[[ Name: invert ]] --[[ Line: 513 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_22 ]]
    assert(#p124 == #p124[1], "matrix not square")
    local v125 = v_u_16.copy(p124)
    local v126 = setmetatable({}, v_u_22)
    local v127 = p124[1][1]
    local v128 = type(v127) == "table" and (v127.zero or 0) or 0
    local v129 = type(v127) == "table" and (v127.one or 1) or 1
    for v130 = 1, #p124 do
        local v131 = {}
        v126[v130] = v131
        for v132 = 1, #p124 do
            local v133 = v130 == v132 and v129 and v129 or v128
            if type(v133) == "table" then
                v133 = v133.copy(v133) or v133
            end;
            v131[v132] = v133
        end;
    end;
    local v134 = v_u_16.concath(v125, v126)
    local v135, v136 = v_u_16.dogauss(v134)
    if v135 then
        return v_u_16.subm(v134, 1, #v134[1] / 2 + 1, #v134, #v134[1]);
    else
        return nil, v136;
    end;
end;
local function f_get_abs_avg(p137, p138) --[[ Name: get_abs_avg ]] --[[ Line: 548 ]]
    local v139 = p137[1][1]
    local v140 = type(v139) == "table" and v139.abs or math.abs
    local v141 = 0
    for v142 = 1, #p137 do
        for v143 = 1, #p137[1] do
            v141 = v141 + v140(p137[v142][v143] - p138[v142][v143])
        end;
    end;
    return v141 / (#p137 * 2);
end;
v_u_16.sqrt = function(p144, p145) --[[ Name: sqrt ]] --[[ Line: 561 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): f_get_abs_avg ]]
    assert(#p144 == #p144[1], "matrix not square")
    local v146 = p145 or (1 / 0)
    local v147 = v_u_16.copy(p144)
    local v148 = v_u_16(#v147, "I")
    local v149 = (1 / 0)
    for _ = 1, v146 do
        local v150 = v_u_16.divnum(v_u_16.add(v147, v_u_16.invert(v148)), 2)
        local v151 = v_u_16.divnum(v_u_16.add(v148, v_u_16.invert(v147)), 2)
        local v152 = f_get_abs_avg(v150, v147)
        if v146 == (1 / 0) and v149 <= v152 then
            return v147, v148, f_get_abs_avg(v_u_16.mul(v147, v147), p144);
        end;
        v149 = v152
        v148 = v151
        v147 = v150
    end;
    return v147, v148, f_get_abs_avg(v_u_16.mul(v147, v147), p144);
end;
v_u_16.root = function(p153, p154, p155) --[[ Name: root ]] --[[ Line: 591 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): f_get_abs_avg ]]
    assert(#p153 == #p153[1], "matrix not square")
    local v156 = p155 or (1 / 0)
    local v157 = v_u_16.copy(p153)
    local v158 = v_u_16.mul(v157:invert(), v157:pow(p154 - 1))
    local v159 = (1 / 0)
    for _ = 1, v156 do
        local v160 = v157:mulnum(p154 - 1):add(v158:invert()):divnum(p154)
        local v161 = v158:mulnum(p154 - 1):add(v157:invert()):divnum(p154):mul(v158:invert():pow(p154 - 2)):mul(v158:mulnum(p154 - 1):add(v157:invert())):divnum(p154)
        local v162 = f_get_abs_avg(v160, v157)
        if v156 == (1 / 0) and v159 <= v162 then
            return v157, v158, f_get_abs_avg(v_u_16.pow(v157, p154), p153);
        end;
        v159 = v162
        v158 = v161
        v157 = v160
    end;
    return v157, v158, f_get_abs_avg(v_u_16.pow(v157, p154), p153);
end;
v_u_16.normf = function(p163) --[[ Name: normf ]] --[[ Line: 626 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    local v164 = v_u_16.type(p163)
    local v165 = 0
    for v166 = 1, #p163 do
        for v167 = 1, #p163[1] do
            local v168 = p163[v166][v167]
            if v164 ~= "number" then
                v168 = v168:abs()
            end;
            v165 = v165 + v168 ^ 2
        end;
    end;
    return (type(v165) == "number" and math.sqrt or v165.sqrt)(v165);
end;
v_u_16.normmax = function(p169) --[[ Name: normmax ]] --[[ Line: 645 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    local v170 = v_u_16.type(p169) == "number" and math.abs or p169[1][1].abs
    local v171 = 0
    for v172 = 1, #p169 do
        for v173 = 1, #p169[1] do
            local v174 = v170(p169[v172][v173])
            if v171 < v174 then
                v171 = v174
            end;
        end;
    end;
    return v171;
end;
local function v_u_177(p175, p176) --[[ Line: 663 ]]
    return math.floor(p175 * p176 + 0.5) / p176;
end;
local function v_u_182(p178, p179) --[[ Line: 666 ]]
    for v180, v181 in ipairs(p178) do
        p178[v180] = math.floor(v181 * p179 + 0.5) / p179
    end;
    return p178;
end;
v_u_16.round = function(p183, p184) --[[ Name: round ]] --[[ Line: 672 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_177, (copy 3): v_u_182 ]]
    local v185 = 10 ^ (p184 or 0)
    local v186 = v_u_16.type(p183) == "number" and v_u_177 or v_u_182
    for v187 = 1, #p183 do
        for v188 = 1, #p183[1] do
            p183[v187][v188] = v186(p183[v187][v188], v185)
        end;
    end;
    return p183;
end;
local function v_u_192(_, p189, p190, p191) --[[ Line: 685 ]]
    return math.random(p189, p190) / p191;
end;
local function v_u_198(p193, p194, p195, p196) --[[ Line: 688 ]]
    for v197 in ipairs(p193) do
        p193[v197] = math.random(p194, p195) / p196
    end;
    return p193;
end;
v_u_16.random = function(p199, p200, p201, p202) --[[ Name: random ]] --[[ Line: 694 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_192, (copy 3): v_u_198 ]]
    local v203 = v_u_16.type(p199) == "number" and v_u_192 or v_u_198
    local v204 = p200 or -10
    local v205 = p201 or 10
    local v206 = p202 or 1
    for v207 = 1, #p199 do
        for v208 = 1, #p199[1] do
            p199[v207][v208] = v203(p199[v207][v208], v204, v205, v206)
        end;
    end;
    return p199;
end;
local function v_u_210(p209) --[[ Line: 726 ]]
    return p209;
end;
local function v_u_215(p211) --[[ Line: 729 ]]
    local v212 = setmetatable({}, (getmetatable(p211)))
    for v213, v214 in ipairs(p211) do
        v212[v213] = v214
    end;
    return v212;
end;
v_u_16.copy = function(p216) --[[ Name: copy ]] --[[ Line: 740 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215, (copy 4): v_u_22 ]]
    local v217 = v_u_16.type(p216) == "number" and v_u_210 or v_u_215
    local v218 = {}
    for v219 = 1, #p216[1] do
        v218[v219] = {}
        for v220 = 1, #p216 do
            v218[v219][v220] = v217(p216[v219][v220])
        end;
    end;
    return setmetatable(v218, v_u_22);
end;
v_u_16.transpose = function(p221) --[[ Name: transpose ]] --[[ Line: 755 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215, (copy 4): v_u_22 ]]
    local v222 = v_u_16.type(p221) == "number" and v_u_210 or v_u_215
    local v223 = {}
    for v224 = 1, #p221[1] do
        v223[v224] = {}
        for v225 = 1, #p221 do
            v223[v224][v225] = v222(p221[v225][v224])
        end;
    end;
    return setmetatable(v223, v_u_22);
end;
v_u_16.subm = function(p226, p227, p228, p229, p230) --[[ Name: subm ]] --[[ Line: 773 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215, (copy 4): v_u_22 ]]
    local v231 = v_u_16.type(p226) == "number" and v_u_210 or v_u_215
    local v232 = {}
    for v233 = p227, p229 do
        local v234 = v233 - p227 + 1
        v232[v234] = {}
        for v235 = p228, p230 do
            v232[v234][v235 - p228 + 1] = v231(p226[v233][v235])
        end;
    end;
    return setmetatable(v232, v_u_22);
end;
v_u_16.concath = function(p236, p237) --[[ Name: concath ]] --[[ Line: 791 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215, (copy 4): v_u_22 ]]
    assert(#p236 == #p237, "matrix size mismatch")
    local v238 = v_u_16.type(p236) == "number" and v_u_210 or v_u_215
    local v239 = #p236[1]
    local v240 = {}
    for v241 = 1, #p236 do
        v240[v241] = {}
        for v242 = 1, v239 do
            v240[v241][v242] = v238(p236[v241][v242])
        end;
        for v243 = 1, #p237[1] do
            v240[v241][v243 + v239] = v238(p237[v241][v243])
        end;
    end;
    return setmetatable(v240, v_u_22);
end;
v_u_16.concatv = function(p244, p245) --[[ Name: concatv ]] --[[ Line: 813 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215, (copy 4): v_u_22 ]]
    assert(#p244[1] == #p245[1], "matrix size mismatch")
    local v246 = v_u_16.type(p244) == "number" and v_u_210 or v_u_215
    local v247 = {}
    for v248 = 1, #p244 do
        v247[v248] = {}
        for v249 = 1, #p244[1] do
            v247[v248][v249] = v246(p244[v248][v249])
        end;
    end;
    local v250 = #v247
    for v251 = 1, #p245 do
        local v252 = v251 + v250
        v247[v252] = {}
        for v253 = 1, #p245[1] do
            v247[v252][v253] = v246(p245[v251][v253])
        end;
    end;
    return setmetatable(v247, v_u_22);
end;
v_u_16.rotl = function(p254) --[[ Name: rotl ]] --[[ Line: 836 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215 ]]
    local v255 = v_u_16:new(#p254[1], #p254)
    local v256 = v_u_16.type(p254) == "number" and v_u_210 or v_u_215
    for v257 = 1, #p254 do
        for v258 = 1, #p254[1] do
            v255[#p254[1] - v258 + 1][v257] = v256(p254[v257][v258])
        end;
    end;
    return v255;
end;
v_u_16.rotr = function(p259) --[[ Name: rotr ]] --[[ Line: 849 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_210, (copy 3): v_u_215 ]]
    local v260 = v_u_16:new(#p259[1], #p259)
    local v261 = v_u_16.type(p259) == "number" and v_u_210 or v_u_215
    for v262 = 1, #p259 do
        for v263 = 1, #p259[1] do
            v260[v263][#p259 - v262 + 1] = v261(p259[v262][v263])
        end;
    end;
    return v260;
end;
local function f_tensor_tostring(p264, p265) --[[ Name: tensor_tostring ]] --[[ Line: 860 ]]
    if not p265 then
        return "[" .. table.concat(p264, ",") .. "]";
    end;
    local v266 = {}
    for v267, v268 in ipairs(p264) do
        v266[v267] = string.format(p265, v268)
    end;
    return "[" .. table.concat(v266, ",") .. "]";
end;
local function f_number_tostring(p269, p270) --[[ Name: number_tostring ]] --[[ Line: 868 ]]
    if p270 then
        p269 = string.format(p270, p269) or p269
    end;
    return p269;
end;
v_u_16.tostring = function(p271, p272) --[[ Name: tostring ]] --[[ Line: 874 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): f_tensor_tostring, (copy 3): f_number_tostring ]]
    local v273 = v_u_16.type(p271)
    local v274 = p271[1][1]
    local v275 = v273 == "tensor" and f_tensor_tostring or (type(v274) == "table" and v274.tostring or f_number_tostring)
    local v276 = {}
    for v277 = 1, #p271 do
        local v278 = {}
        for v279 = 1, #p271[1] do
            v278[v279] = v275(p271[v277][v279], p272)
        end;
        v276[v277] = table.concat(v278, "\t")
    end;
    return table.concat(v276, "\n");
end;
v_u_16.print = function(...) --[[ Name: print ]] --[[ Line: 892 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    print(v_u_16.tostring(...))
end;
v_u_16.latex = function(p280, p281) --[[ Name: latex ]] --[[ Line: 898 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): f_tensor_tostring, (copy 3): f_number_tostring ]]
    local v282 = "$\\left( \\begin{array}{" .. string.rep(p281 or "c", #p280[1]) .. "}\n"
    local v283 = v_u_16.type(p280) == "tensor" and f_tensor_tostring or f_number_tostring
    for v284 = 1, #p280 do
        local v285 = v282 .. "\t" .. v283(p280[v284][1])
        for v286 = 2, #p280[1] do
            v285 = v285 .. " & " .. v283(p280[v284][v286])
        end;
        if v284 == #p280 then
            v282 = v285 .. "\n"
        else
            v282 = v285 .. " \\\\\n"
        end;
    end;
    return v282 .. "\\end{array} \\right)$";
end;
v_u_16.size = function(p287) --[[ Name: size ]] --[[ Line: 937 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    if v_u_16.type(p287) == "tensor" then
        return #p287, #p287[1], #p287[1][1];
    else
        return #p287, #p287[1];
    end;
end;
v_u_16.setelement = function(p288, p289, p290, p291) --[[ Name: setelement ]] --[[ Line: 956 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    if v_u_16.getelement(p288, p289, p290) then
        p288[p289][p290] = p291
        return 1;
    end;
end;
v_u_16.cross = function(_, _) --[[ Name: cross ]] --[[ Line: 995 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    return setmetatable({
        {},
        {},
        {}
    }, v_u_22);
end;
v_u_16.replace = function(p292, p293, ...) --[[ Name: replace ]] --[[ Line: 1012 ]]
    --[[ Upvalues: (copy 1): v_u_22 ]]
    local v294 = {}
    for v295 = 1, #p292 do
        local v296 = p292[v295]
        local v297 = {}
        for v298 = 1, #v296 do
            v297[v298] = p293(v296[v298], ...)
        end;
        v294[v295] = v297
    end;
    return setmetatable(v294, v_u_22);
end;
v_u_16.elementstostrings = function(p299) --[[ Name: elementstostrings ]] --[[ Line: 1028 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    local v300 = p299[1][1]
    return v_u_16.replace(p299, type(v300) == "table" and v300.tostring or tostring);
end;
v_u_16.solve = function(p301) --[[ Name: solve ]] --[[ Line: 1036 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_22 ]]
    assert(v_u_16.type(p301) == "symbol", "matrix not of type \'symbol\'")
    local v302 = {}
    for v303 = 1, #p301 do
        v302[v303] = {}
        for v304 = 1, #p301[1] do
            v302[v303][v304] = tonumber(loadstring("return " .. p301[v303][v304][1])())
        end;
    end;
    return setmetatable(v302, v_u_22);
end;
v_u_22.__mul = function(p305, p306) --[[ Line: 1070 ]]
    --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_16 ]]
    if getmetatable(p305) == v_u_22 then
        if getmetatable(p306) == v_u_22 then
            return v_u_16.mul(p305, p306);
        else
            return v_u_16.mulnum(p305, p306);
        end;
    else
        return v_u_16.mulnum(p306, p305);
    end;
end;
v_u_22.__div = function(p307, p308) --[[ Line: 1080 ]]
    --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_16 ]]
    if getmetatable(p307) == v_u_22 then
        if getmetatable(p308) == v_u_22 then
            return v_u_16.div(p307, p308);
        else
            return v_u_16.divnum(p307, p308);
        end;
    else
        return v_u_16.mulnum(v_u_16.invert(p308), p307);
    end;
end;
local v_u_311 = {
    ["*"] = function(p309) --[[ Line: 1102 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.conjugate(p309);
    end,
    ["T"] = function(p310) --[[ Line: 1104 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16.transpose(p310);
    end
}
v_u_22.__pow = function(p312, p313) --[[ Line: 1106 ]]
    --[[ Upvalues: (copy 1): v_u_311, (copy 2): v_u_16 ]]
    return v_u_311[p313] and v_u_311[p313](p312) or v_u_16.pow(p312, p313);
end;
for v314, v315 in pairs(v_u_16) do
    v_u_22.__index[v314] = v315
end;
local v_u_323 = {
    ["to"] = v_u_323.new,
    ["tostring"] = function(p316, p317) --[[ Name: tostring ]] --[[ Line: 1168 ]]
        return string.format(p317, p316[1]);
    end,
    ["__eq"] = function(p318, p319) --[[ Name: __eq ]] --[[ Line: 1231 ]]
        return p318[1] == p319[1];
    end,
    ["__tostring"] = function(p320) --[[ Name: __tostring ]] --[[ Line: 1235 ]]
        return p320[1];
    end,
    ["__concat"] = function(p321, p322) --[[ Name: __concat ]] --[[ Line: 1239 ]]
        return tostring(p321) .. tostring(p322);
    end
}
v_u_323.__index = v_u_323
v_u_323.new = function(p324) --[[ Name: new ]] --[[ Line: 1156 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return setmetatable({ (tostring(p324)) }, v_u_323);
end;
setmetatable(v_u_323, {
    ["__call"] = function(_, p325) --[[ Name: __call ]] --[[ Line: 1164 ]]
        --[[ Upvalues: (copy 1): v_u_323 ]]
        return v_u_323.to(p325);
    end
})
v_u_323.type = function(p326) --[[ Name: type ]] --[[ Line: 1173 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    if getmetatable(p326) == v_u_323 then
        return "symbol";
    end;
end;
v_u_323.gsub = function(p327, p328, p329) --[[ Name: gsub ]] --[[ Line: 1181 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to(string.gsub(p327[1], p328, p329));
end;
v_u_323.makereplacer = function(...) --[[ Name: makereplacer ]] --[[ Line: 1189 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    local v330 = { ... }
    local v_u_331 = {}
    for v332 = 1, #v330, 2 do
        v_u_331[v330[v332]] = v330[v332 + 1]
    end;
    local function f_func(p333) --[[ Name: func ]] --[[ Line: 1195 ]]
        --[[ Upvalues: (copy 1): v_u_331 ]]
        return v_u_331[p333] or p333;
    end;
    return function(p334) --[[ Line: 1196 ]]
        --[[ Upvalues: (ref 1): v_u_323, (copy 2): f_func ]]
        return v_u_323.to(string.gsub(p334[1], "%a", f_func));
    end;
end;
v_u_323.abs = function(p335) --[[ Name: abs ]] --[[ Line: 1202 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to("(" .. p335[1] .. "):abs()");
end;
v_u_323.sqrt = function(p336) --[[ Name: sqrt ]] --[[ Line: 1207 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to("(" .. p336[1] .. "):sqrt()");
end;
v_u_323.__add = function(p337, p338) --[[ Name: __add ]] --[[ Line: 1211 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to(p337 .. "+" .. p338);
end;
v_u_323.__sub = function(p339, p340) --[[ Name: __sub ]] --[[ Line: 1215 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to(p339 .. "-" .. p340);
end;
v_u_323.__mul = function(p341, p342) --[[ Name: __mul ]] --[[ Line: 1219 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to("(" .. p341 .. ")*(" .. p342 .. ")");
end;
v_u_323.__div = function(p343, p344) --[[ Name: __div ]] --[[ Line: 1223 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to("(" .. p343 .. ")/(" .. p344 .. ")");
end;
v_u_323.__pow = function(p345, p346) --[[ Name: __pow ]] --[[ Line: 1227 ]]
    --[[ Upvalues: (copy 1): v_u_323 ]]
    return v_u_323.to("(" .. p345 .. ")^(" .. p346 .. ")");
end;
v_u_16.symbol = v_u_323
return v_u_16;
