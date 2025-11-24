-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v2 = {}
local v_u_3 = {
    {
        ["ID"] = 2,
        ["DisplayRequirement"] = 1,
        ["Count"] = 1,
        ["Materials"] = { 10 }
    },
    {
        ["ID"] = 3,
        ["DisplayRequirement"] = 2,
        ["Count"] = 1,
        ["Materials"] = {
            [2] = 10
        }
    },
    {
        ["ID"] = 4,
        ["DisplayRequirement"] = 3,
        ["Count"] = 1,
        ["Materials"] = {
            [3] = 10
        }
    },
    {
        ["ID"] = 1,
        ["DisplayRequirement"] = 2,
        ["Count"] = 3,
        ["Materials"] = {
            [2] = 1
        }
    },
    {
        ["ID"] = 2,
        ["DisplayRequirement"] = 3,
        ["Count"] = 3,
        ["Materials"] = {
            [3] = 1
        }
    },
    {
        ["ID"] = 6,
        ["DisplayRequirement"] = 5,
        ["Count"] = 1,
        ["Materials"] = {
            [5] = 10
        }
    },
    {
        ["ID"] = 7,
        ["DisplayRequirement"] = 6,
        ["Count"] = 1,
        ["Materials"] = {
            [6] = 10
        }
    },
    {
        ["ID"] = 8,
        ["DisplayRequirement"] = 7,
        ["Count"] = 1,
        ["Materials"] = {
            [7] = 10
        }
    },
    {
        ["ID"] = 5,
        ["DisplayRequirement"] = 6,
        ["Count"] = 3,
        ["Materials"] = {
            [6] = 1
        }
    },
    {
        ["ID"] = 6,
        ["DisplayRequirement"] = 7,
        ["Count"] = 3,
        ["Materials"] = {
            [7] = 1
        }
    },
    {
        ["ID"] = 10,
        ["DisplayRequirement"] = 9,
        ["Count"] = 1,
        ["Materials"] = {
            [9] = 10
        }
    },
    {
        ["ID"] = 11,
        ["DisplayRequirement"] = 10,
        ["Count"] = 1,
        ["Materials"] = {
            [10] = 10
        }
    },
    {
        ["ID"] = 12,
        ["DisplayRequirement"] = 11,
        ["Count"] = 1,
        ["Materials"] = {
            [11] = 10
        }
    },
    {
        ["ID"] = 9,
        ["DisplayRequirement"] = 10,
        ["Count"] = 3,
        ["Materials"] = {
            [10] = 1
        }
    },
    {
        ["ID"] = 10,
        ["DisplayRequirement"] = 11,
        ["Count"] = 3,
        ["Materials"] = {
            [11] = 1
        }
    },
    {
        ["ID"] = 14,
        ["DisplayRequirement"] = 13,
        ["Count"] = 1,
        ["Materials"] = {
            [13] = 10
        }
    },
    {
        ["ID"] = 15,
        ["DisplayRequirement"] = 14,
        ["Count"] = 1,
        ["Materials"] = {
            [14] = 10
        }
    },
    {
        ["ID"] = 16,
        ["DisplayRequirement"] = 15,
        ["Count"] = 1,
        ["Materials"] = {
            [15] = 10
        }
    },
    {
        ["ID"] = 13,
        ["DisplayRequirement"] = 14,
        ["Count"] = 3,
        ["Materials"] = {
            [14] = 1
        }
    },
    {
        ["ID"] = 14,
        ["DisplayRequirement"] = 15,
        ["Count"] = 3,
        ["Materials"] = {
            [15] = 1
        }
    },
    {
        ["ID"] = 18,
        ["DisplayRequirement"] = 17,
        ["Count"] = 1,
        ["Materials"] = {
            [17] = 10
        }
    },
    {
        ["ID"] = 19,
        ["DisplayRequirement"] = 18,
        ["Count"] = 1,
        ["Materials"] = {
            [18] = 10
        }
    },
    {
        ["ID"] = 20,
        ["DisplayRequirement"] = 19,
        ["Count"] = 1,
        ["Materials"] = {
            [19] = 10
        }
    },
    {
        ["ID"] = 17,
        ["DisplayRequirement"] = 18,
        ["Count"] = 3,
        ["Materials"] = {
            [18] = 1
        }
    },
    {
        ["ID"] = 18,
        ["DisplayRequirement"] = 19,
        ["Count"] = 3,
        ["Materials"] = {
            [19] = 1
        }
    },
    {
        ["ID"] = 32,
        ["DisplayRequirement"] = 4,
        ["Count"] = 1,
        ["Materials"] = {
            [4] = 3
        }
    },
    {
        ["ID"] = 32,
        ["DisplayRequirement"] = 8,
        ["Count"] = 1,
        ["Materials"] = {
            [8] = 3
        }
    },
    {
        ["ID"] = 32,
        ["DisplayRequirement"] = 12,
        ["Count"] = 1,
        ["Materials"] = {
            [12] = 3
        }
    },
    {
        ["ID"] = 32,
        ["DisplayRequirement"] = 16,
        ["Count"] = 1,
        ["Materials"] = {
            [16] = 3
        }
    },
    {
        ["ID"] = 32,
        ["DisplayRequirement"] = 20,
        ["Count"] = 1,
        ["Materials"] = {
            [20] = 3
        }
    },
    {
        ["ID"] = 33,
        ["DisplayRequirement"] = 4,
        ["Count"] = 1,
        ["Materials"] = {
            [4] = 2
        }
    },
    {
        ["ID"] = 33,
        ["DisplayRequirement"] = 8,
        ["Count"] = 1,
        ["Materials"] = {
            [8] = 2
        }
    },
    {
        ["ID"] = 33,
        ["DisplayRequirement"] = 12,
        ["Count"] = 1,
        ["Materials"] = {
            [12] = 2
        }
    },
    {
        ["ID"] = 33,
        ["DisplayRequirement"] = 16,
        ["Count"] = 1,
        ["Materials"] = {
            [16] = 2
        }
    },
    {
        ["ID"] = 33,
        ["DisplayRequirement"] = 20,
        ["Count"] = 1,
        ["Materials"] = {
            [20] = 2
        }
    },
    {
        ["ID"] = 148,
        ["DisplayRequirement"] = 2,
        ["Count"] = 1,
        ["Materials"] = {
            [2] = 5
        }
    },
    {
        ["ID"] = 148,
        ["DisplayRequirement"] = 6,
        ["Count"] = 1,
        ["Materials"] = {
            [6] = 5
        }
    },
    {
        ["ID"] = 148,
        ["DisplayRequirement"] = 10,
        ["Count"] = 1,
        ["Materials"] = {
            [10] = 5
        }
    },
    {
        ["ID"] = 148,
        ["DisplayRequirement"] = 14,
        ["Count"] = 1,
        ["Materials"] = {
            [14] = 5
        }
    },
    {
        ["ID"] = 148,
        ["DisplayRequirement"] = 18,
        ["Count"] = 1,
        ["Materials"] = {
            [18] = 5
        }
    }
}
local v_u_5 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 58 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v4 = {
            ["has_display_requirement_materialid"] = function(_) --[[ Name: has_display_requirement_materialid ]] --[[ Line: 64 ]]
                return false, -1;
            end
        }
        v4.get_requirements = function(_, _) --[[ Name: get_requirements ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("MaterialRecipeBase must implement get_requirements")
        end;
        v4.get_material_id = function(_) --[[ Name: get_material_id ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("MaterialRecipeBase must implement get_gear_id")
        end;
        v4.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("MaterialRecipeBase must implement get_count")
        end;
        return v4;
    end
}
v2.add_to_craftdatabase = function(_, p6) --[[ Name: add_to_craftdatabase ]] --[[ Line: 69 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_5 ]]
    for v7 = 1, #v_u_3 do
        local v8 = v_u_3[v7]
        local l_ID_0 = v8.ID
        local l_Materials_0 = v8.Materials
        local l_Count_0 = v8.Count
        for v9, _ in pairs(l_Materials_0) do
            if p6:get_material(v9) == nil then
                v_u_1:errf("CraftDatabase does not contain material(%d)", v9)
            end;
        end;
        local v_u_10, v_u_11
        if v8.DisplayRequirement == nil then
            v_u_10 = -1
            v_u_11 = false
        else
            v_u_10 = v8.DisplayRequirement
            v_u_11 = true
        end;
        p6:add_to_material_recipe_dict(v7, ((function() --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): l_ID_0, (copy 3): l_Materials_0, (copy 4): l_Count_0, (ref 5): v_u_11, (ref 6): v_u_10 ]]
            local v12 = v_u_5:new()
            v12.get_material_id = function(_) --[[ Name: get_material_id ]] --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): l_ID_0 ]]
                return l_ID_0;
            end;
            v12.get_requirements = function(_, p13) --[[ Name: get_requirements ]] --[[ Line: 97 ]]
                --[[ Upvalues: (ref 1): l_Materials_0 ]]
                p13:clear()
                for v14, v15 in pairs(l_Materials_0) do
                    p13:add(v14, v15)
                end;
            end;
            v12.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): l_Count_0 ]]
                return l_Count_0;
            end;
            if v_u_11 then
                v12.has_display_requirement_materialid = function(_) --[[ Name: has_display_requirement_materialid ]] --[[ Line: 105 ]]
                    --[[ Upvalues: (ref 1): v_u_10 ]]
                    return true, v_u_10;
                end;
            end;
            return v12;
        end)()))
    end;
end;
return v2;
