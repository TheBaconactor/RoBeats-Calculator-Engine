-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

local v_u_8 = {
    ["TextLabel"] = function(p1, _, p2, _) --[[ Line: 4 ]]
        p1.TextTransparency = p2
        if p1.TextStrokeColor3 ~= Color3.new() then
            p1.TextStrokeTransparency = p2
        end;
    end,
    ["TextBox"] = function(p3, _, p4, _) --[[ Line: 10 ]]
        p3.TextTransparency = p4
        p3.TextStrokeTransparency = p4
    end,
    ["ImageLabel"] = function(p5, p6, _, p7) --[[ Line: 14 ]]
        p5.ImageTransparency = p7
        if #p5.Image == 0 then
            p5.BackgroundTransparency = p6
        end;
    end
}
local function f__r_set_alpha_perform(p9, p10) --[[ Name: _r_set_alpha_perform ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    local l_Name_0 = p9.Name
    local v11, v12
    if string.sub(l_Name_0, 1, 1) == "{" then
        local v13 = string.sub(l_Name_0, 1, string.find(l_Name_0, "}"))
        v11 = p10
        v12 = v11
        local v14 = v11
        v11 = v12
        v14 = v12
        local v15 = 1
        while true do
            local v16 = v15 + 1
            local v17 = string.find(v13, "=", v16)
            local v18 = string.find(v13, ",", v16)
            v15 = string.find(v13, "}", v16)
            if v17 == nil or v15 == nil then
                break;
            end;
            local v19 = string.sub(l_Name_0, v16, v17 - 1)
            local v20
            if v18 == nil then
                v20 = string.sub(l_Name_0, v17 + 1, v15 - 1)
            else
                v20 = string.sub(l_Name_0, v17 + 1, v18 - 1)
                v15 = v18
            end;
            if v19 == "BackgroundAlpha" then
                p10 = SPUtil:tra(tonumber(v20) * SPUtil:tra(p10))
            elseif v19 == "TextAlpha" then
                v12 = SPUtil:tra(tonumber(v20) * SPUtil:tra(v12))
            elseif v19 == "ImageAlpha" then
                v11 = SPUtil:tra(tonumber(v20) * SPUtil:tra(v11))
            end;
        end;
    else
        v11 = p10
        v12 = v11
        local v21 = v11
        v11 = v12
        v21 = v12
    end;
    local v22 = v_u_8[p9.ClassName]
    if v22 == nil then
        return false;
    end;
    v22(p9, p10, v12, v11)
    return true;
end;
local function f__r_set_alpha(p23, p24, p25, p26) --[[ Name: _r_set_alpha ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): f__r_set_alpha_perform, (copy 2): f__r_set_alpha ]]
    if p25 ~= nil then
        for v27 = 1, p25:count() do
            if p23.Name == p25:get(v27) then
                return;
            end;
        end;
    end;
    if p26 ~= nil and f__r_set_alpha_perform(p23, p24) == true then
        p26[#p26 + 1] = p23
    end;
    for _, v28 in pairs(p23:GetChildren()) do
        f__r_set_alpha(v28, p24, p25, p26)
    end;
end;
SPUtil.r_set_alpha_generate_name = function(_, p29, p30) --[[ Name: r_set_alpha_generate_name ]] --[[ Line: 90 ]]
    local v31 = "{"
    for v32, v33 in pairs(p29) do
        if v32 == "BackgroundAlpha" or (v32 == "ImageAlpha" or v32 == "TextAlpha") then
            v31 = v31 .. v32 .. "=" .. tostring(v33) .. ","
        else
            SPUtil:errf("r_set_alpha_generate_name unknown key(%s)", v32)
        end;
    end;
    local v34 = v31 .. "}"
    if typeof(p30) == "string" then
        return v34 .. p30;
    else
        local l_Name_1 = p30.Name
        local v35 = string.find(l_Name_1, "}")
        if v35 == nil then
            return v34 .. l_Name_1;
        else
            return v34 .. string.sub(l_Name_1, v35 + 1);
        end;
    end;
end;
local v_u_36 = {}
SPUtil.r_set_alpha = function(_, p37, p38, p39) --[[ Name: r_set_alpha ]] --[[ Line: 117 ]]
    --[[ Upvalues: (copy 1): v_u_36, (copy 2): f__r_set_alpha_perform, (copy 3): f__r_set_alpha ]]
    SPUtil:profilebegin("r_set_alpha")
    local v40 = SPUtil:tra(p38)
    local v41 = v_u_36[p37.Name]
    if v41 == nil or (v41.Root ~= p37 or tick() - v41.Time >= 1) then
        local v42 = {}
        f__r_set_alpha(p37, v40, p39, v42)
        v_u_36[p37.Name] = {
            ["Time"] = tick(),
            ["CacheList"] = v42,
            ["Root"] = p37
        }
    else
        local l_CacheList_0 = v41.CacheList
        for v43 = 1, #l_CacheList_0 do
            f__r_set_alpha_perform(l_CacheList_0[v43], v40)
        end;
    end;
    SPUtil:profileend()
    return p37;
end;
return {};
