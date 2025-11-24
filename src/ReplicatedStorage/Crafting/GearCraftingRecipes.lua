-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Crafting.GearRecipeBase)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v4 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v5 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v6 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v7 = {}
local v_u_8 = {
    {
        ["ID"] = 44,
        ["DisplayRequirement"] = 21,
        ["Materials"] = {
            [21] = 2,
            [19] = 3,
            [15] = 3
        }
    },
    {
        ["ID"] = 45,
        ["DisplayRequirement"] = 21,
        ["Materials"] = {
            [21] = 4,
            [19] = 5,
            [15] = 5
        }
    },
    {
        ["ID"] = 46,
        ["DisplayRequirement"] = 21,
        ["Materials"] = {
            [21] = 7,
            [3] = 4,
            [15] = 4,
            [11] = 4
        }
    },
    {
        ["ID"] = 47,
        ["DisplayRequirement"] = 21,
        ["Materials"] = {
            [21] = 10,
            [15] = 6,
            [16] = 1
        },
        [15] = 10
    },
    {
        ["ID"] = 48,
        ["DisplayRequirement"] = 21,
        ["Materials"] = {
            [21] = 20,
            [12] = 1,
            [16] = 2
        },
        [19] = 10
    },
    {
        ["ID"] = 49,
        ["DisplayRequirement"] = 21,
        ["Materials"] = {
            [21] = 15,
            [12] = 1,
            [16] = 1
        },
        [11] = 10
    },
    {
        ["ID"] = 50,
        ["DisplayRequirement"] = 23,
        ["Materials"] = {
            [23] = 2,
            [3] = 3,
            [15] = 3
        }
    },
    {
        ["ID"] = 51,
        ["DisplayRequirement"] = 23,
        ["Materials"] = {
            [23] = 4,
            [3] = 5,
            [7] = 5
        }
    },
    {
        ["ID"] = 52,
        ["DisplayRequirement"] = 23,
        ["Materials"] = {
            [23] = 7,
            [3] = 4,
            [11] = 4,
            [15] = 4
        }
    },
    {
        ["ID"] = 53,
        ["DisplayRequirement"] = 23,
        ["Materials"] = {
            [23] = 10,
            [15] = 6,
            [16] = 1,
            [11] = 10
        }
    },
    {
        ["ID"] = 54,
        ["DisplayRequirement"] = 23,
        ["Materials"] = {
            [23] = 20,
            [8] = 1,
            [16] = 2,
            [7] = 10
        }
    },
    {
        ["ID"] = 55,
        ["DisplayRequirement"] = 23,
        ["Materials"] = {
            [23] = 15,
            [8] = 1,
            [16] = 1,
            [3] = 10
        }
    },
    {
        ["ID"] = 56,
        ["DisplayRequirement"] = 22,
        ["Materials"] = {
            [22] = 2,
            [19] = 3,
            [15] = 3
        }
    },
    {
        ["ID"] = 57,
        ["DisplayRequirement"] = 22,
        ["Materials"] = {
            [22] = 4,
            [19] = 5,
            [7] = 5
        }
    },
    {
        ["ID"] = 58,
        ["DisplayRequirement"] = 22,
        ["Materials"] = {
            [22] = 7,
            [3] = 4,
            [15] = 4,
            [7] = 4
        }
    },
    {
        ["ID"] = 59,
        ["DisplayRequirement"] = 22,
        ["Materials"] = {
            [22] = 10,
            [7] = 6,
            [8] = 1,
            [15] = 10
        }
    },
    {
        ["ID"] = 60,
        ["DisplayRequirement"] = 22,
        ["Materials"] = {
            [22] = 20,
            [8] = 2,
            [16] = 1,
            [3] = 10
        }
    },
    {
        ["ID"] = 61,
        ["DisplayRequirement"] = 22,
        ["Materials"] = {
            [22] = 15,
            [8] = 1,
            [16] = 1,
            [19] = 10
        }
    }
}
local v_u_9 = 71
local v_u_10 = 57
local function _(p11) --[[ Name: itr_add_crafting_recipe ]] --[[ Line: 104 ]]
    --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10 ]]
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = p11
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
end;
local v12 = v_u_9
local v13 = v_u_10
for _, v14 in pairs({
    v5.Blue,
    v5.Green,
    v5.Orange,
    v5.Purple,
    v5.Red
}) do
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v12,
        ["DisplayRequirement"] = v13,
        ["Materials"] = {
            [v13] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T2)] = 5,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 5
        }
    }
    v_u_9 = v12 + 1
    v_u_10 = v13 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T2)] = 5,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 5
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T2)] = 5,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 5
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T2)] = 5,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 5
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T2)] = 5,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 5
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T2)] = 5,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 5
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 25,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T4)] = 10
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T4)] = 5,
            [v4:brass_token_id()] = 10
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 25,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T4)] = 10
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T3)] = 25,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T4)] = 10
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T4)] = 5,
            [v4:silver_token_id()] = 10
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_9,
        ["DisplayRequirement"] = v_u_10,
        ["Materials"] = {
            [v_u_10] = 1,
            [v4:color_and_tier_to_material_id(v14, v6.Tier.T4)] = 5,
            [v4:gold_token_id()] = 10
        }
    }
    v_u_9 = v_u_9 + 1
    v_u_10 = v_u_10 + 1
    v12 = v_u_9
    v13 = v_u_10
end;
if v12 ~= 131 or v13 ~= 117 then
    error("GearCraftingRecipes unexpected end value")
end;
local v_u_15 = 131
local function _(p16) --[[ Name: itr_add_crafting_recipe ]] --[[ Line: 189 ]]
    --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_15 ]]
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v_u_15,
        ["GearTutorial"] = true,
        ["Materials"] = p16
    }
    v_u_15 = v_u_15 + 1
end;
local v17 = v_u_15
for _, v18 in pairs({
    v5.Blue,
    v5.Green,
    v5.Orange,
    v5.Purple,
    v5.Red
}) do
    v_u_8[#v_u_8 + 1] = {
        ["ID"] = v17,
        ["GearTutorial"] = true,
        ["Materials"] = {
            [v4:color_and_tier_to_material_id(v18, v6.Tier.T1)] = 5,
            [v4:color_and_tier_to_material_id(v18, v6.Tier.T2)] = 3
        }
    }
    v_u_15 = v17 + 1
    v17 = v_u_15
end;
if v17 ~= 136 then
    error("GearCraftingRecipes unexpected end value")
end;
v7.add_to_craftdatabase = function(_, p19) --[[ Name: add_to_craftdatabase ]] --[[ Line: 204 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_1 ]]
    for v20 = 1, #v_u_8 do
        local v21 = v_u_8[v20]
        local l_ID_0 = v21.ID
        local l_Materials_0 = v21.Materials
        if v_u_2:singleton():get_equipment_for_id(l_ID_0) == nil then
            v_u_3:errf("GearCraftingRecipes no key for id(%s)", (tostring(l_ID_0)))
        end;
        for v22, _ in pairs(l_Materials_0) do
            if p19:get_material(v22) == nil then
                v_u_3:errf("CraftDatabase does not contain material(%d)", v22)
            end;
        end;
        local v_u_23, v_u_24
        if v21.DisplayRequirement == nil then
            v_u_23 = false
            v_u_24 = -1
        else
            v_u_24 = v21.DisplayRequirement
            v_u_23 = true
        end;
        local v_u_25 = v21.GearTutorial == true
        p19:add_to_gear_recipe_dict(v20, ((function() --[[ Line: 232 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): l_ID_0, (copy 3): l_Materials_0, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_25 ]]
            local v26 = v_u_1:new()
            v26.get_gear_id = function(_) --[[ Name: get_gear_id ]] --[[ Line: 234 ]]
                --[[ Upvalues: (ref 1): l_ID_0 ]]
                return l_ID_0;
            end;
            v26.get_requirements = function(_, p27) --[[ Name: get_requirements ]] --[[ Line: 235 ]]
                --[[ Upvalues: (ref 1): l_Materials_0 ]]
                p27:clear()
                for v28, v29 in pairs(l_Materials_0) do
                    p27:add(v28, v29)
                end;
            end;
            if v_u_23 then
                v26.has_display_requirement_materialid = function(_) --[[ Name: has_display_requirement_materialid ]] --[[ Line: 242 ]]
                    --[[ Upvalues: (ref 1): v_u_24 ]]
                    return true, v_u_24;
                end;
            end;
            if v_u_25 then
                v26.is_gear_tutorial = function(_) --[[ Name: is_gear_tutorial ]] --[[ Line: 247 ]]
                    return true;
                end;
            end;
            return v26;
        end)()))
    end;
end;
return v7;
