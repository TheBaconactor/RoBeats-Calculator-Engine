-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {
            ["has_display_requirement_materialid"] = function(_) --[[ Name: has_display_requirement_materialid ]] --[[ Line: 16 ]]
                return false, -1;
            end,
            ["is_gear_tutorial"] = function(_) --[[ Name: is_gear_tutorial ]] --[[ Line: 20 ]]
                return false;
            end
        }
        v2.get_requirements = function(_, _) --[[ Name: get_requirements ]] --[[ Line: 8 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("GearRecipeBase must implement get_requirements")
        end;
        v2.get_gear_id = function(_) --[[ Name: get_gear_id ]] --[[ Line: 12 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("GearRecipeBase must implement get_gear_id")
        end;
        return v2;
    end
};
