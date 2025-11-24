-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.LVector3)
local v5 = require(game.ReplicatedStorage.Shared.LCFrame)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_10 = {
    ["Type"] = {
        ["Cylinder"] = "CylinderHandleAdornment",
        ["Sphere"] = "SphereHandleAdornment"
    },
    ["cylinder_adorn_copy_properties"] = function(_, p6, p7) --[[ Name: cylinder_adorn_copy_properties ]] --[[ Line: 74 ]]
        p7.Color3 = p6.Color3
        p7.Transparency = p6.Transparency
        p7.AlwaysOnTop = p6.AlwaysOnTop
        p7.Height = p6.Height
        p7.Radius = p6.Radius
        p7.ZIndex = p6.ZIndex
    end,
    ["sphere_adorn_copy_properties"] = function(_, p8, p9) --[[ Name: sphere_adorn_copy_properties ]] --[[ Line: 83 ]]
        p9.Color3 = p8.Color3
        p9.Transparency = p8.Transparency
        p9.AlwaysOnTop = p8.AlwaysOnTop
        p9.Radius = p8.Radius
        p9.ZIndex = p8.ZIndex
    end
}
local v_u_11 = CFrame.new(0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 1, 0)
local v_u_12 = v5.new()
v_u_12:from_cframe(v_u_11)
v_u_10.cylinder_up_cframe = function(_) --[[ Name: cylinder_up_cframe ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    return v_u_11;
end;
v_u_10.cylinder_up_cframe_lv = function(_) --[[ Name: cylinder_up_cframe_lv ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return v_u_12;
end;
local l_Folder_0 = Instance.new("Folder")
l_Folder_0.Name = v_u_2:gen_name("AdornPool")
l_Folder_0.Parent = game.Workspace
v_u_10.verify_all_adorns_in_folder_are_hidden = function(_) --[[ Name: verify_all_adorns_in_folder_are_hidden ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): l_Folder_0, (copy 2): v_u_4 ]]
    local v_u_13 = true
    local v15, v16 = pcall(function() --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): l_Folder_0, (ref 2): v_u_13 ]]
        for _, v14 in pairs(l_Folder_0:GetChildren()) do
            if v14.Visible == true then
                v_u_13 = false
                v14.Visible = false
                v14.Transparency = 1
            end;
        end;
    end)
    if v15 ~= true then
        v_u_4:warnf("AdornPool:verify_all_adorns_in_folder_are_hidden failed: %s", v16)
    end;
    return v_u_13;
end;
v_u_10.new = function(_) --[[ Name: new ]] --[[ Line: 94 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_10, (copy 3): v_u_3, (copy 4): v_u_2, (copy 5): l_Folder_0 ]]
    local v20 = {
        ["prealloc_adorn_of_type"] = function(p17, p18, p19) --[[ Name: prealloc_adorn_of_type ]] --[[ Line: 109 ]]
            for _ = 1, p19 do
                p17:repool(p17:create_adorn_of_type(p18))
            end;
        end
    }
    local v_u_21 = v_u_1:new()
    v20.prepool = function(p22) --[[ Name: prepool ]] --[[ Line: 99 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        p22:prealloc_adorn_of_type(v_u_10.Type.Cylinder, 300)
        p22:prealloc_adorn_of_type(v_u_10.Type.Sphere, 50)
    end;
    v20.shuffle = function(_) --[[ Name: shuffle ]] --[[ Line: 104 ]]
        --[[ Upvalues: (copy 1): v_u_21, (ref 2): v_u_10 ]]
        v_u_21:list_of(v_u_10.Type.Cylinder):shuffle()
        v_u_21:list_of(v_u_10.Type.Sphere):shuffle()
    end;
    v20.create_adorn_of_type = function(_, p23) --[[ Name: create_adorn_of_type ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2, (ref 3): l_Folder_0 ]]
        local v24 = v_u_3:get_adornpool_root()
        local v25 = Instance.new(p23)
        v25.Name = v_u_2:gen_name(p23)
        v25.Adornee = v24
        v25.AlwaysOnTop = false
        v25.Parent = l_Folder_0
        return v25;
    end;
    v20.depool = function(p26, p27) --[[ Name: depool ]] --[[ Line: 126 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        local v28
        if v_u_21:count_of(p27) > 0 then
            v28 = v_u_21:pop_back_from(p27)
        else
            v28 = p26:create_adorn_of_type(p27)
        end;
        v28.Visible = true
        v28.Transparency = 0
        return v28;
    end;
    v20.repool = function(_, p29) --[[ Name: repool ]] --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        p29.Visible = false
        p29.Transparency = 1
        v_u_21:push_back_to(p29.ClassName, p29)
    end;
    return v20;
end;
return v_u_10;
