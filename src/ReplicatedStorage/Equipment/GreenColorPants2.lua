-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Avatar.ColorGearParticles)
local v_u_5 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v6 = v_u_1:new()
v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 9 ]]
    return "Legendary Vibe Ringleader\'s Slacks";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v6.apply_appearance = function(_, p7) --[[ Name: apply_appearance ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    v_u_1:pants_base_apply(p7, "rbxassetid://5512366109")
    v_u_4:attach_color_particle(v_u_5.Green, p7)
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorGreen] = 20,
        [v_u_3.Type.ColorOrange] = 9,
        [v_u_3.Type.ComboMultiplier] = 9
    };
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 26 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 29 ]]
    return 3;
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 32 ]]
    return "rbxassetid://5555598362";
end;
return v6;
