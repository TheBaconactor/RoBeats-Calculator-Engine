-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = {
    ["Blue"] = 0,
    ["Green"] = 1,
    ["Orange"] = 2,
    ["Purple"] = 3,
    ["Red"] = 4,
    ["color_none"] = function(_) --[[ Name: color_none ]] --[[ Line: 13 ]]
        return -1;
    end
}
local v_u_4 = v2:new():push_back_table_list({
    v_u_3.Blue,
    v_u_3.Green,
    v_u_3.Orange,
    v_u_3.Purple,
    v_u_3.Red
})
v_u_3.colors_list = function(_) --[[ Name: colors_list ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    return v_u_4;
end;
v_u_3.color_to_name = function(_, p5) --[[ Name: color_to_name ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    v_u_1:is_enum_member(p5, v_u_3)
    return p5 == v_u_3.Blue and "Chill" or (p5 == v_u_3.Green and "Vibe" or (p5 == v_u_3.Purple and "Flow" or (p5 == v_u_3.Red and "Rush" or (p5 == v_u_3.Orange and "Beat" or ""))));
end;
v_u_3.color_to_iconimage = function(_, p6) --[[ Name: color_to_iconimage ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    v_u_1:is_enum_member(p6, v_u_3)
    return p6 == v_u_3.Blue and "rbxassetid://5452134846" or (p6 == v_u_3.Green and "rbxassetid://5452134959" or (p6 == v_u_3.Purple and "rbxassetid://5452135280" or (p6 == v_u_3.Red and "rbxassetid://5452135417" or (p6 == v_u_3.Orange and "rbxassetid://5453620524" or ""))));
end;
v_u_3.color_to_textimage = function(_, p7) --[[ Name: color_to_textimage ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    v_u_1:is_enum_member(p7, v_u_3)
    return p7 == v_u_3.Blue and "rbxassetid://5452134305" or (p7 == v_u_3.Green and "rbxassetid://5452134163" or (p7 == v_u_3.Purple and "rbxassetid://5452134585" or (p7 == v_u_3.Red and "rbxassetid://5452134716" or "rbxassetid://5453620426")));
end;
v_u_3.color_to_color3 = function(_, p8) --[[ Name: color_to_color3 ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    v_u_1:is_enum_member(p8, v_u_3)
    if p8 == v_u_3.Blue then
        return Color3.fromRGB(129, 171, 249);
    elseif p8 == v_u_3.Green then
        return Color3.fromRGB(138, 251, 131);
    elseif p8 == v_u_3.Purple then
        return Color3.fromRGB(243, 119, 248);
    elseif p8 == v_u_3.Red then
        return Color3.fromRGB(253, 105, 141);
    else
        return Color3.fromRGB(253, 140, 57);
    end;
end;
v_u_3.render_color_section = function(_, p9, p10, p11) --[[ Name: render_color_section ]] --[[ Line: 86 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    if p11:count() == 0 then
        p9.Visible = false
        p10.Visible = false
        return;
    elseif p11:count() == 1 then
        p9.Visible = true
        p9.Image = v_u_3:color_to_iconimage(p11:get(1))
        p10.Visible = false
    else
        p9.Visible = true
        p9.Image = v_u_3:color_to_iconimage(p11:get(1))
        p10.Visible = true
        p10.Image = v_u_3:color_to_iconimage(p11:get(2))
    end;
end;
v_u_3.elements_list_get_string = function(_, p12) --[[ Name: elements_list_get_string ]] --[[ Line: 102 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v13 = ""
    for v14 = 1, p12:count() do
        v13 = v13 .. v_u_3:color_to_name(p12:get(v14))
        if v14 < p12:count() then
            v13 = v13 .. ", "
        end;
    end;
    return v13;
end;
return v_u_3;
