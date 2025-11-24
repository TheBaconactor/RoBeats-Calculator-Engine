-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Legendary Musketeer\'s Hat";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
local function _(p5, p6) --[[ Name: make_weld ]] --[[ Line: 15 ]]
    local l_Weld_0 = Instance.new("Weld")
    l_Weld_0.Part0 = p5
    l_Weld_0.Part1 = p6
    l_Weld_0.C1 = CFrame.new(0, 0, 0)
    l_Weld_0.C0 = l_Weld_0.Part0.CFrame:inverse() * l_Weld_0.Part1.CFrame
    l_Weld_0.Parent = script.Parent
    return l_Weld_0;
end;
v4.apply_appearance = function(p7, p8) --[[ Name: apply_appearance ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v9, _, v10 = v_u_1:create_accessory_base(p8, p7:get_name(), "HatAttachment", "rbxassetid://2621417574", "rbxassetid://2307345974")
    v10.Offset = Vector3.new(0, 0.2, -0.1)
    v10.Scale = Vector3.new(0.625, 0.625, 0.625)
    v_u_1:attach_character_accessory(p8, v9)
    local v11, _, v12 = v_u_1:create_accessory_base(p8, p7:get_name() .. "(Feather)", "HatAttachment", "rbxassetid://2621249973", "rbxassetid://2307345974")
    v12.Offset = Vector3.new(-0.45, 0.4, 0.5)
    v12.Scale = Vector3.new(0.5, 0.5, 0.55)
    v12.Parent.Transparency = 0.01
    v_u_1:attach_character_accessory(p8, v11)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 59 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 62 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 13,
        [v_u_3.Type.ColorGreen] = 13,
        [v_u_3.Type.ComboMultiplier] = 6,
        [v_u_3.Type.FeverTime] = 2
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 73 ]]
    return "rbxassetid://2623571078";
end;
return v4;
