-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUIChild)
return {
    ["new"] = function(_, p_u_2) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v3 = {}
        local v_u_4 = nil
        local v_u_5 = nil
        local v_u_6 = 1
        local v_u_7 = 1
        v3.cons = function(p8) --[[ Name: cons ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (copy 3): p_u_2, (ref 4): v_u_5 ]]
            v_u_4 = v_u_1:get_list_of_children_of_classname(p_u_2, "ImageLabel")
            v_u_5 = v_u_1:get_list_of_children_of_classname(p_u_2, "TextLabel")
            return p8;
        end;
        v3.set_alpha = function(_, p9) --[[ Name: set_alpha ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_1, (ref 3): v_u_4, (ref 4): v_u_5, (copy 5): p_u_2, (ref 6): v_u_7 ]]
            if v_u_6 ~= p9 then
                v_u_6 = p9
                v_u_1:list_set_alpha_name(v_u_4, {
                    ["ImageAlpha"] = v_u_6
                })
                v_u_1:list_set_alpha_name(v_u_5, {
                    ["TextAlpha"] = v_u_6
                })
                v_u_1:r_set_alpha(p_u_2, v_u_7)
            end;
        end;
        v3.set_parent_alpha = function(_, p10) --[[ Name: set_parent_alpha ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_1, (copy 3): p_u_2 ]]
            if v_u_7 ~= p10 then
                v_u_7 = p10
                v_u_1:r_set_alpha(p_u_2, v_u_7)
            end;
        end;
        v3:cons()
        return v3;
    end
};
