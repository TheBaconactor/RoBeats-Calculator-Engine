-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 7 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v10 = {
            ["cons"] = function(_) end,
            ["depool_instance_type"] = function(p3, p4) --[[ Name: depool_instance_type ]] --[[ Line: 35 ]]
                local v5 = p3:depool(p4)
                if v5 == nil then
                    v5 = Instance.new(p4)
                end;
                return v5;
            end,
            ["depool_key_instance_type"] = function(p6, p7, p8) --[[ Name: depool_key_instance_type ]] --[[ Line: 43 ]]
                local v9 = p6:depool(p7)
                if v9 == nil then
                    v9 = Instance.new(p8)
                end;
                return v9;
            end
        }
        local l_Folder_0 = Instance.new("Folder", game.Lighting)
        l_Folder_0.Name = "ObjPooledParent"
        local v_u_11 = v_u_1:new()
        v10.repool = function(_, p12, p13) --[[ Name: repool ]] --[[ Line: 18 ]]
            --[[ Upvalues: (copy 1): v_u_11, (ref 2): v_u_2, (copy 3): l_Folder_0 ]]
            v_u_11:push_back_to(p12, p13)
            if v_u_2.ObjectPoolToFolder == true then
                p13.Parent = l_Folder_0
            else
                p13.Parent = nil
            end;
        end;
        v10.depool = function(_, p14) --[[ Name: depool ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): v_u_11 ]]
            if v_u_11:count_of(p14) == 0 then
                return nil;
            else
                return v_u_11:pop_back_from(p14);
            end;
        end;
        v10:cons()
        return v10;
    end
};
