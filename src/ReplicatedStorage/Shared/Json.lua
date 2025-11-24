-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

local v_u_1 = {
    ["\\"] = "\\\\",
    ["\""] = "\\\"",
    ["\8"] = "\\b",
    ["\f"] = "\\f",
    ["\n"] = "\\n",
    ["\r"] = "\\r",
    ["\t"] = "\\t"
}
local v_u_2 = {
    ["\\/"] = "/"
}
local v_u_3 = nil
local v4 = {
    ["_version"] = "0.1.0"
}
for v5, v6 in pairs(v_u_1) do
    v_u_2[v6] = v5
end;
local function f_escape_char(p7) --[[ Name: escape_char ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1[p7] or string.format("\\u%04x", p7:byte());
end;
local v_u_11 = {
    ["nil"] = function(_) --[[ Name: encode_nil ]] --[[ Line: 39 ]]
        return "null";
    end,
    ["string"] = function(p8) --[[ Name: encode_string ]] --[[ Line: 86 ]]
        --[[ Upvalues: (copy 1): f_escape_char ]]
        return "\"" .. p8:gsub("[%z\1-\31\\\"]", f_escape_char) .. "\"";
    end,
    ["number"] = function(p9) --[[ Name: encode_number ]] --[[ Line: 91 ]]
        return string.format("%.14g", p9);
    end,
    ["boolean"] = tostring,
    ["userdata"] = function(p10) --[[ Name: encode_userdata ]] --[[ Line: 99 ]]
        return string.format("[%s](%s)", typeof(p10), (tostring(p10)));
    end
}
v_u_11.table = function(p12, p13) --[[ Name: encode_table ]] --[[ Line: 44 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    local v14 = {}
    local v15 = p13 or {}
    if v15[p12] then
        error("circular reference")
    end;
    v15[p12] = true
    if p12[1] == nil and next(p12) ~= nil then
        for v16, v17 in pairs(p12) do
            table.insert(v14, v_u_3(v16, v15) .. ":" .. v_u_3(v17, v15))
        end;
        v15[p12] = nil
        return "{" .. table.concat(v14, ",") .. "}";
    end;
    local v18 = 0
    for _ in pairs(p12) do
        v18 = v18 + 1
    end;
    for _, v19 in ipairs(p12) do
        table.insert(v14, v_u_3(v19, v15))
    end;
    v15[p12] = nil
    return "[" .. table.concat(v14, ",") .. "]";
end;
local function v_u_23(p20, p21) --[[ Line: 114 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    local v22 = v_u_11[type(p20)]
    if v22 then
        return v22(p20, p21);
    end;
end;
v4.encode = function(p24) --[[ Name: encode ]] --[[ Line: 124 ]]
    --[[ Upvalues: (ref 1): v_u_23 ]]
    return v_u_23(p24);
end;
local v_u_25 = nil
local function f_create_set(...) --[[ Name: create_set ]] --[[ Line: 135 ]]
    local v26 = {}
    for v27 = 1, select("#", ...) do
        v26[select(v27, ...)] = true
    end;
    return v26;
end;
local v_u_28 = f_create_set(" ", "\t", "\r", "\n")
local v_u_29 = f_create_set(" ", "\t", "\r", "\n", "]", "}", ",")
local v_u_30 = f_create_set("\\", "/", "\"", "b", "f", "n", "r", "t", "u")
local v_u_31 = f_create_set("true", "false", "null")
local v_u_32 = {
    ["true"] = true,
    ["false"] = false,
    ["null"] = nil
}
local function f_next_char(p33, p34, p35, p36) --[[ Name: next_char ]] --[[ Line: 155 ]]
    for v37 = p34, #p33 do
        if p35[p33:sub(v37, v37)] ~= p36 then
            return v37;
        end;
    end;
    return #p33 + 1;
end;
local function f_decode_error(p38, p39, p40) --[[ Name: decode_error ]] --[[ Line: 165 ]]
    local v41 = 1
    local v42 = 1
    for v43 = 1, p39 - 1 do
        v41 = v41 + 1
        if p38:sub(v43, v43) == "\n" then
            v42 = v42 + 1
            v41 = 1
        end;
    end;
    error(string.format("%s at line %d col %d", p40, v42, v41))
end;
local function f_codepoint_to_utf8(p44) --[[ Name: codepoint_to_utf8 ]] --[[ Line: 179 ]]
    local l_floor_0 = math.floor
    if p44 <= 127 then
        return string.char(p44);
    end;
    if p44 <= 2047 then
        return string.char(l_floor_0(p44 / 64) + 192, p44 % 64 + 128);
    end;
    if p44 <= 65535 then
        return string.char(l_floor_0(p44 / 4096) + 224, l_floor_0(p44 % 4096 / 64) + 128, p44 % 64 + 128);
    end;
    if p44 <= 1114111 then
        return string.char(l_floor_0(p44 / 262144) + 240, l_floor_0(p44 % 262144 / 4096) + 128, l_floor_0(p44 % 4096 / 64) + 128, p44 % 64 + 128);
    end;
    error(string.format("invalid unicode codepoint \'%x\'", p44))
end;
local function f_parse_unicode_escape(p45) --[[ Name: parse_unicode_escape ]] --[[ Line: 196 ]]
    --[[ Upvalues: (copy 1): f_codepoint_to_utf8 ]]
    local v46 = tonumber(p45:sub(3, 6), 16)
    local v47 = tonumber(p45:sub(9, 12), 16)
    if v47 then
        return f_codepoint_to_utf8((v46 - 55296) * 1024 + (v47 - 56320) + 65536);
    else
        return f_codepoint_to_utf8(v46);
    end;
end;
local function f_parse_number(p48, p49) --[[ Name: parse_number ]] --[[ Line: 261 ]]
    --[[ Upvalues: (copy 1): f_next_char, (copy 2): v_u_29, (copy 3): f_decode_error ]]
    local v50 = f_next_char(p48, p49, v_u_29)
    local v51 = p48:sub(p49, v50 - 1)
    local v52 = tonumber(v51)
    if not v52 then
        f_decode_error(p48, p49, "invalid number \'" .. v51 .. "\'")
    end;
    return v52, v50;
end;
local function f_parse_literal(p53, p54) --[[ Name: parse_literal ]] --[[ Line: 272 ]]
    --[[ Upvalues: (copy 1): f_next_char, (copy 2): v_u_29, (copy 3): v_u_31, (copy 4): f_decode_error, (copy 5): v_u_32 ]]
    local v55 = f_next_char(p53, p54, v_u_29)
    local v56 = p53:sub(p54, v55 - 1)
    if not v_u_31[v56] then
        f_decode_error(p53, p54, "invalid literal \'" .. v56 .. "\'")
    end;
    return v_u_32[v56], v55;
end;
local v_u_79 = {
    ["0"] = f_parse_number,
    ["1"] = f_parse_number,
    ["2"] = f_parse_number,
    ["3"] = f_parse_number,
    ["4"] = f_parse_number,
    ["5"] = f_parse_number,
    ["6"] = f_parse_number,
    ["7"] = f_parse_number,
    ["8"] = f_parse_number,
    ["9"] = f_parse_number,
    ["-"] = f_parse_number,
    ["t"] = f_parse_literal,
    ["f"] = f_parse_literal,
    ["n"] = f_parse_literal,
    ["["] = function(p57, p58) --[[ Name: parse_array ]] --[[ Line: 282 ]]
        --[[ Upvalues: (copy 1): f_next_char, (copy 2): v_u_28, (ref 3): v_u_25, (copy 4): f_decode_error ]]
        local v59 = p58 + 1
        local v60 = {}
        local v61 = 1
        while true do
            local v62 = f_next_char(p57, v59, v_u_28, true)
            if p57:sub(v62, v62) == "]" then
                v59 = v62 + 1
                break;
            end;
            local v63, v64 = v_u_25(p57, v62)
            v60[v61] = v63
            v61 = v61 + 1
            local v65 = f_next_char(p57, v64, v_u_28, true)
            local v66 = p57:sub(v65, v65)
            v59 = v65 + 1
            if v66 == "]" then
                break;
            end;
            if v66 ~= "," then
                f_decode_error(p57, v59, "expected \']\' or \',\'")
            end;
        end;
        return v60, v59;
    end,
    ["{"] = function(p67, p68) --[[ Name: parse_object ]] --[[ Line: 309 ]]
        --[[ Upvalues: (copy 1): f_next_char, (copy 2): v_u_28, (copy 3): f_decode_error, (ref 4): v_u_25 ]]
        local v69 = p68 + 1
        local v70 = {}
        while true do
            local v71 = f_next_char(p67, v69, v_u_28, true)
            if p67:sub(v71, v71) == "}" then
                v69 = v71 + 1
                break;
            end;
            if p67:sub(v71, v71) ~= "\"" then
                f_decode_error(p67, v71, "expected string for key")
            end;
            local v72, v73 = v_u_25(p67, v71)
            local v74 = f_next_char(p67, v73, v_u_28, true)
            if p67:sub(v74, v74) ~= ":" then
                f_decode_error(p67, v74, "expected \':\' after key")
            end;
            local v75, v76 = v_u_25(p67, (f_next_char(p67, v74 + 1, v_u_28, true)))
            v70[v72] = v75
            local v77 = f_next_char(p67, v76, v_u_28, true)
            local v78 = p67:sub(v77, v77)
            v69 = v77 + 1
            if v78 == "}" then
                break;
            end;
            if v78 ~= "," then
                f_decode_error(p67, v69, "expected \'}\' or \',\'")
            end;
        end;
        return v70, v69;
    end
}
v_u_79["\""] = function(p80, p81) --[[ Name: parse_string ]] --[[ Line: 208 ]]
    --[[ Upvalues: (copy 1): f_decode_error, (copy 2): v_u_30, (copy 3): f_parse_unicode_escape, (copy 4): v_u_2 ]]
    local v82 = false
    local v83 = nil
    local v84 = false
    local v85 = false
    for v86 = p81 + 1, #p80 do
        local v87 = p80:byte(v86)
        if v87 < 32 then
            f_decode_error(p80, v86, "control character in string")
        end;
        if v83 == 92 then
            if v87 == 117 then
                local v88 = p80:sub(v86 + 1, v86 + 5)
                if not v88:find("%x%x%x%x") then
                    f_decode_error(p80, v86, "invalid unicode escape in string")
                end;
                if v88:find("^[dD][89aAbB]") then
                    v84 = true
                else
                    v85 = true
                end;
            else
                local v89 = string.char(v87)
                if v_u_30[v89] then
                    v82 = true
                else
                    f_decode_error(p80, v86, "invalid escape char \'" .. v89 .. "\' in string")
                    v82 = true
                end;
            end;
            v83 = nil
        else
            if v87 == 34 then
                local v90 = p80:sub(p81 + 1, v86 - 1)
                if v84 then
                    v90 = v90:gsub("\\u[dD][89aAbB]..\\u....", f_parse_unicode_escape)
                end;
                if v85 then
                    v90 = v90:gsub("\\u....", f_parse_unicode_escape)
                end;
                if v82 then
                    v90 = v90:gsub("\\.", v_u_2)
                end;
                return v90, v86 + 1;
            end;
            v83 = v87
        end;
    end;
    f_decode_error(p80, p81, "expected closing quote for string")
end
v_u_25 = function(p91, p92) --[[ Line: 367 ]]
    --[[ Upvalues: (copy 1): v_u_79, (copy 2): f_decode_error ]]
    local v93 = p91:sub(p92, p92)
    local v94 = v_u_79[v93]
    if v94 then
        return v94(p91, p92);
    end;
    f_decode_error(p91, p92, "unexpected character \'" .. v93 .. "\'")
end
v4.decode = function(p95) --[[ Name: decode ]] --[[ Line: 377 ]]
    --[[ Upvalues: (ref 1): v_u_25, (copy 2): f_next_char, (copy 3): v_u_28 ]]
    return v_u_25(p95, (f_next_char(p95, 1, v_u_28, true)));
end;
return v4;
