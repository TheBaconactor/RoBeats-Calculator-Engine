-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {
            ["get_icon"] = function(_) --[[ Name: get_icon ]] --[[ Line: 12 ]]
                return "";
            end
        }
        v2.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("EquipmentUpgradeBase must implement get_name")
        end;
        v2.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 9 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return v_u_1:errf("EquipmentUpgradeBase must implement get_gear_statmodifierobj");
        end;
        v2.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 10 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("EquipmentUpgradeBase must implement get_gear_power")
        end;
        v2.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 11 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("EquipmentUpgradeBase must implement get_craft_materials")
        end;
        return v2;
    end
};
