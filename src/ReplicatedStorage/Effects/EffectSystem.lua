-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v3 = {}
        local l_Folder_0 = Instance.new("Folder", game.Workspace)
        l_Folder_0.Name = "EffectRoot"
        l_Folder_0.Name = v_u_2:gen_name(l_Folder_0.Name)
        local v_u_4 = v_u_1:new()
        v3.get_effect_root = function(_) --[[ Name: get_effect_root ]] --[[ Line: 15 ]]
            --[[ Upvalues: (copy 1): l_Folder_0 ]]
            return l_Folder_0;
        end;
        v3.teardown = function(_, p5) --[[ Name: teardown ]] --[[ Line: 17 ]]
            --[[ Upvalues: (copy 1): v_u_4, (copy 2): l_Folder_0 ]]
            for v6 = v_u_4:count(), 1, -1 do
                v_u_4:get(v6):do_remove(p5)
            end;
            v_u_4:clear()
            l_Folder_0:Destroy()
        end;
        v3.update = function(_, p7, p8) --[[ Name: update ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            for v9 = v_u_4:count(), 1, -1 do
                local v10 = v_u_4:get(v9)
                if v10.update ~= nil then
                    v10:update(p7, p8)
                end;
                if v10:should_remove(p8) then
                    v10:do_remove(p8)
                    v_u_4:remove_at(v9)
                end;
            end;
        end;
        v3.post_update = function(_, p11, p12) --[[ Name: post_update ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            for v13 = v_u_4:count(), 1, -1 do
                local v14 = v_u_4:get(v13)
                if v14.post_update ~= nil then
                    v14:post_update(p11, p12)
                end;
            end;
        end;
        v3.add_effect = function(_, p15) --[[ Name: add_effect ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): l_Folder_0, (copy 2): v_u_4 ]]
            p15:add_to_parent(l_Folder_0)
            v_u_4:push_back(p15)
            return p15;
        end;
        return v3;
    end,
    ["EffectBase"] = function(_) --[[ Name: EffectBase ]] --[[ Line: 58 ]]
        return {
            ["add_to_parent"] = function(_, _, _) --[[ Name: add_to_parent ]] --[[ Line: 61 ]]
                error("EffectBase must implement add_to_parent")
            end,
            ["update"] = function(_, _, _) --[[ Name: update ]] --[[ Line: 62 ]]
                error("EffectBase must implement update")
            end,
            ["should_remove"] = function(_, _) --[[ Name: should_remove ]] --[[ Line: 63 ]]
                error("EffectBase must implement should_remove")
            end,
            ["do_remove"] = function(_, _) --[[ Name: do_remove ]] --[[ Line: 64 ]]
                error("EffectBase must implement do_remove")
            end
        };
    end
};
