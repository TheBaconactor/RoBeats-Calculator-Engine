-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPUtil)
local v73 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_9, (copy 4): v_u_6, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_3, (copy 8): v_u_8, (copy 9): v_u_7 ]]
        local v10 = {}
        local v_u_11 = v_u_2:new()
        local v_u_12 = v_u_2:new()
        local v_u_13 = v_u_1:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_13, (ref 3): v_u_9, (ref 4): v_u_2, (ref 5): v_u_6, (ref 6): v_u_5, (copy 7): v_u_12, (ref 8): v_u_4, (copy 9): v_u_11 ]]
            v_u_1:push_if_not_nil(v_u_13, v_u_9:if_exists(function() --[[ Line: 23 ]]
                return game.Workspace.ModelLoadDB;
            end))
            v_u_1:push_if_not_nil(v_u_13, v_u_9:if_exists(function() --[[ Line: 24 ]]
                return game.ReplicatedStorage.ModelLoadDB;
            end))
            for _, v14 in v_u_13:key_itr() do
                local v15 = v_u_2:new()
                for v16, _ in v_u_6:get_categories_to_ids():key_itr() do
                    local v17 = v14:FindFirstChild(v16)
                    if v15 ~= nil then
                        v15:add(v16, v17)
                    end;
                end;
                for v18, v19 in v15:key_itr() do
                    local v20 = v19:FindFirstChild("Default")
                    if v20 ~= nil then
                        v_u_5:is_false(v_u_12:contains(v18))
                        v_u_12:add(v18, v20)
                    end;
                end;
                for v21, v22 in v15:key_itr() do
                    for _, v23 in pairs(v22:GetChildren()) do
                        local l_Name_0 = v23.Name
                        if l_Name_0 ~= "Default" then
                            local v24 = v_u_6:get_category_name_to_id(v21):get(l_Name_0)
                            if v24 == nil then
                                v_u_4:errf("Preloaded model(%s) no assigned id (not defined in ModelLoadDBAsset)", v23:GetFullName())
                            end;
                            v_u_11:add(v24, v23)
                        end;
                    end;
                end;
            end;
            for v25, _ in v_u_6:get_categories_to_ids():key_itr() do
                v_u_5:is_non_nil(v_u_12:get(v25), v25)
            end;
        end;
        v10.get_loaded_models_count = function(_) --[[ Name: get_loaded_models_count ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): v_u_11 ]]
            return v_u_11:count();
        end;
        local v_u_26 = nil
        local v_u_27 = v_u_2:new()
        v10.init_as_server = function(_, p28) --[[ Name: init_as_server ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_2, (ref 3): v_u_6, (ref 4): v_u_5, (copy 5): v_u_11, (ref 6): v_u_4, (ref 7): v_u_3, (copy 8): v_u_27 ]]
            v_u_26 = p28
            local l_ModelLoadDB_0 = game.ServerStorage.ModelLoadDB
            local v29 = v_u_2:new()
            for _, v30 in pairs(l_ModelLoadDB_0:GetChildren()) do
                v29:add(v30.Name, v30)
            end;
            for v31, v32 in v_u_6:get_categories_to_ids():key_itr() do
                v_u_5:is_true(v29:contains(v31))
                for _, v33 in v32:key_itr() do
                    if v_u_11:contains(v33) ~= true then
                        local v34 = v_u_6:get_id_to_name():get(v33)
                        local v35 = v29:get(v31):FindFirstChild(v34)
                        if v35 == nil then
                            v_u_4:errf("ModelLoadDB:init_as_server missing asset category(%s) name(%s)", v31, v34)
                        end;
                        v_u_11:add(v33, v35)
                    end;
                end;
            end;
            v_u_26._evt:wait_on_event(v_u_3.EVT_ModelLoadDB_ClientRequestLoad, function(p36, p37) --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_11, (ref 4): v_u_4, (ref 5): v_u_27, (ref 6): v_u_26, (ref 7): v_u_3 ]]
                v_u_5:is_true(v_u_6:get_id_to_name():contains(p37))
                if v_u_6:get_id_to_name():contains(p37) ~= true or v_u_11:contains(p37) ~= true then
                    return v_u_4:warnf("EVT_ModelLoadDB_ClientRequestLoad invalid ModelLoadDBAsset(%s)", (tostring(p37)));
                end;
                local l_UserId_0 = p36.UserId
                local l_PlayerGui_0 = p36.PlayerGui
                if l_PlayerGui_0 == nil then
                    return v_u_4:warnf("EVT_ModelLoadDB_ClientRequestLoad playergui is nil");
                end;
                if v_u_27:contains(l_UserId_0) ~= true then
                    local l_ScreenGui_0 = Instance.new("ScreenGui")
                    l_ScreenGui_0.ResetOnSpawn = false
                    l_ScreenGui_0.Name = "ModelLoadDB"
                    l_ScreenGui_0.Parent = l_PlayerGui_0
                    v_u_27:add(l_UserId_0, l_ScreenGui_0)
                end;
                local v38 = v_u_27:get(l_UserId_0)
                if v38.Parent ~= l_PlayerGui_0 then
                    v38.Parent = l_PlayerGui_0
                end;
                local v39 = string.format("%s_%d", v_u_6:get_id_to_name():get(p37), p37)
                local v40 = v38:FindFirstChild(v39)
                if v40 ~= nil then
                    v_u_4:warnf("EVT_ModelLoadDB_ClientRequestLoad model(%d) already replicated to client", p37)
                end;
                if v40 == nil then
                    v40 = v_u_11:get(p37):Clone()
                    v40.Name = v39
                    v40.Parent = v38
                end;
                v_u_26._evt:fire_event_to_client(v_u_3.EVT_ModelLoadDB_ServerLoadResponse, p36, p37, v40)
            end)
            v_u_4:puts("ModelLoadDB:init_as_server completed")
        end;
        v10.server_player_disconnecting = function(_, p41) --[[ Name: server_player_disconnecting ]] --[[ Line: 134 ]]
            --[[ Upvalues: (copy 1): v_u_27 ]]
            v_u_27:remove(p41)
        end;
        local v_u_42 = nil
        v10.init_as_client = function(_, p43) --[[ Name: init_as_client ]] --[[ Line: 142 ]]
            --[[ Upvalues: (copy 1): v_u_13, (ref 2): v_u_42, (ref 3): v_u_3, (ref 4): v_u_4, (ref 5): v_u_8, (ref 6): v_u_9, (copy 7): v_u_11 ]]
            for _, v44 in v_u_13:key_itr() do
                v44.Parent = nil
            end;
            local l_Folder_0 = Instance.new("Folder", game.Lighting)
            l_Folder_0.Name = "ModelLoadDB_Loaded"
            v_u_42 = p43
            v_u_42._evt:wait_on_event(v_u_3.EVT_ModelLoadDB_ServerLoadResponse, function(p_u_45, p_u_46) --[[ Line: 151 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): l_Folder_0, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_11 ]]
                if p_u_46 == nil then
                    return v_u_4:warnf("EVT_ModelLoadDB_ServerLoadResponse model is nil");
                end;
                p_u_46.Parent = l_Folder_0
                if v_u_8.ModelDB_DebugExtraLoadTime == true then
                    spawn(function() --[[ Line: 156 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_4, (ref 3): v_u_11, (copy 4): p_u_45, (copy 5): p_u_46 ]]
                        local v47 = v_u_9:rand_rangef(1, 10)
                        v_u_4:warnf("ModelDB_DebugExtraLoadTime(%.2f)", v47)
                        while v47 > 0 do
                            v47 = v47 - 0.1
                            wait(0.1)
                        end;
                        v_u_4:warnf("ModelDB_DebugExtraLoadTime finished")
                        v_u_11:add(p_u_45, p_u_46)
                    end)
                else
                    v_u_11:add(p_u_45, p_u_46)
                end;
                if v_u_9:is_dev_build() then
                    v_u_4:puts("Loaded model(%s) total(%d)", p_u_46.Name, v_u_11:count())
                end;
            end)
        end;
        local v_u_48 = v_u_7:new()
        local function f_load_model_client(p_u_49, p_u_50) --[[ Name: load_model_client ]] --[[ Line: 177 ]]
            --[[ Upvalues: (copy 1): v_u_11, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_4, (copy 5): v_u_48, (ref 6): v_u_42, (ref 7): v_u_3, (ref 8): v_u_6 ]]
            if v_u_11:contains(p_u_49) then
                local v_u_51 = v_u_11:get(p_u_49)
                if v_u_8.ModelDB_DebugClientExtraLoadTimeOnCached == true then
                    return spawn(function() --[[ Line: 181 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_4, (copy 3): p_u_50, (copy 4): v_u_51 ]]
                        local v52 = v_u_9:rand_rangef(3, 6)
                        v_u_4:warnf("ModelDB_DebugClientExtraLoadTimeOnCached(%.2f)", v52)
                        while v52 > 0 do
                            v52 = v52 - 0.1
                            wait(0.1)
                        end;
                        v_u_4:warnf("ModelDB_DebugClientExtraLoadTimeOnCached finished")
                        return p_u_50(v_u_51);
                    end);
                else
                    return p_u_50(v_u_51);
                end;
            else
                v_u_48:push_back_to(p_u_49, p_u_50)
                if v_u_48:count_of(p_u_49) <= 1 then
                    v_u_42._evt:fire_event_to_server(v_u_3.EVT_ModelLoadDB_ClientRequestLoad, p_u_49)
                    spawn(function() --[[ Line: 200 ]]
                        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_49, (ref 3): v_u_11, (ref 4): v_u_4, (ref 5): v_u_42, (ref 6): v_u_48 ]]
                        local v53 = tick()
                        local v54
                        if v_u_6:get_id_category_table(p_u_49) == v_u_6.NPC then
                            v54 = 15
                        else
                            v54 = 10
                        end;
                        while v_u_11:contains(p_u_49) ~= true do
                            if v54 < tick() - v53 then
                                v_u_4:warnf("ModelLoadDB:load_model_client timed out")
                                break;
                            end;
                            wait(0.1)
                        end;
                        v_u_42._update_enqueue_fn:enqueue_function(function() --[[ Line: 215 ]]
                            --[[ Upvalues: (ref 1): v_u_48, (ref 2): p_u_49, (ref 3): v_u_11 ]]
                            for _, v55 in v_u_48:list_of(p_u_49):key_itr() do
                                v55(v_u_11:get(p_u_49))
                            end;
                            v_u_48:list_of(p_u_49):clear()
                        end)
                    end)
                end;
            end;
        end;
        local function f_load_model(p56, p_u_57) --[[ Name: load_model ]] --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_26, (copy 2): v_u_11, (ref 3): v_u_42, (copy 4): f_load_model_client, (ref 5): v_u_4 ]]
            local function f_clone_and_pass_into_loaded_fn(p58) --[[ Name: clone_and_pass_into_loaded_fn ]] --[[ Line: 227 ]]
                --[[ Upvalues: (copy 1): p_u_57 ]]
                local v59
                if p58 then
                    v59 = p58:Clone()
                else
                    v59 = nil
                end;
                p_u_57(v59)
            end;
            if v_u_26 then
                local v60 = v_u_11:get(p56)
                local v61
                if v60 then
                    v61 = v60:Clone()
                else
                    v61 = nil
                end;
                p_u_57(v61)
                return;
            elseif v_u_42 then
                f_load_model_client(p56, f_clone_and_pass_into_loaded_fn)
            else
                v_u_4:warnf("ModelLoadDB _server and _local_services nil")
                p_u_57(nil)
            end;
        end;
        v10.get_category_default = function(_, p62) --[[ Name: get_category_default ]] --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (copy 3): v_u_12 ]]
            v_u_5:is_enum_member(p62, v_u_6.Category)
            return v_u_12:get(p62):Clone();
        end;
        v10.load_model_category = function(p_u_63, p_u_64, p_u_65, p_u_66) --[[ Name: load_model_category ]] --[[ Line: 249 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_9, (ref 4): v_u_4, (copy 5): f_load_model, (ref 6): v_u_8 ]]
            v_u_5:is_enum_member(p_u_65, v_u_6.Category)
            local function f_loaded_fn(p_u_67) --[[ Name: loaded_fn ]] --[[ Line: 251 ]]
                --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_66, (ref 3): v_u_4, (copy 4): p_u_64, (copy 5): p_u_65 ]]
                local v68, v69 = v_u_9:try(function() --[[ Line: 252 ]]
                    --[[ Upvalues: (ref 1): p_u_66, (copy 2): p_u_67 ]]
                    p_u_66(p_u_67)
                end)
                if v68 ~= true then
                    v_u_4:warnf("ModelLoadDB load_model_category(%s,%s) failed, error(%s)\n%s", tostring(p_u_64), tostring(p_u_65), tostring(v69.Error), (tostring(v69.StackTrace)))
                end;
            end;
            f_load_model(p_u_64, function(p70) --[[ Line: 260 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): f_loaded_fn, (copy 3): p_u_63, (copy 4): p_u_65, (ref 5): v_u_4, (copy 6): p_u_64 ]]
                if v_u_8.ModelDB_AlwaysLoadDefault == true then
                    return f_loaded_fn(p_u_63:get_category_default(p_u_65));
                elseif p70 == nil then
                    v_u_4:warnf("ModelLoadDB load_model_category(%s,%s) failed, loading default", tostring(p_u_64), (tostring(p_u_65)))
                    p_u_63:add_id_with_error(p_u_64)
                    f_loaded_fn(p_u_63:get_category_default(p_u_65))
                else
                    f_loaded_fn(p70)
                end;
            end)
        end;
        local v_u_71 = v_u_2:new()
        v10.get_error_id_set = function(_) --[[ Name: get_error_id_set ]] --[[ Line: 276 ]]
            --[[ Upvalues: (copy 1): v_u_71 ]]
            return v_u_71;
        end;
        v10.add_id_with_error = function(_, p72) --[[ Name: add_id_with_error ]] --[[ Line: 277 ]]
            --[[ Upvalues: (copy 1): v_u_71 ]]
            if p72 ~= nil then
                v_u_71:add_set(p72)
            end;
        end;
        f_cons()
        return v10;
    end
}
local v_u_74 = v73:new()
v73.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 288 ]]
    --[[ Upvalues: (copy 1): v_u_74 ]]
    return v_u_74;
end;
return v73;
